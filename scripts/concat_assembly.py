"""Stream-copy reel assembly: concat demuxer first, bounded re-encode second.

The old reel path decoded three 1080p60 branches inside one ``filter_complex``
and re-encoded 10 minutes in a single graph; FFmpeg's concat filter buffered
frames across branches and the machine paged.  This module builds four
*already-normalized* segments and lets the concat demuxer join them:

    intro.mp4            (CFR 60, 1920x1080, yuv420p, AAC 48k stereo)
    clip-01.seg.mp4      (video stream-copied, audio fade-out)
    transition.mp4       (0.5 s card, 60 fps, silent AAC)
    clip-02.seg.mp4      (video stream-copied, audio fade-in)

    ffmpeg -f concat -safe 0 -i concat.txt -c copy ...

Only audio is ever re-encoded here (bed mix + boundary fades); the video
packets are copied, so memory stays flat and the only large write is the
final file.  If the segments cannot be joined by copy (codec mismatch or a
decode error at a join), ``build_concat_assembly`` falls back to one bounded
re-encode through the concat demuxer -- still no frame-buffering filter graph.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import auto_clip as ac

SAMPLE_RATE = 48000
CHANNELS = 2
# One video track timescale for every segment: the clips are 1/19001, the
# QSV intro/card 1/15360, and mixed base times make concat copy misplace PTS.
VIDEO_TIMESCALE = "15360"


class ConcatFallback(RuntimeError):
    """The stream-copy path cannot be used; the caller may re-encode instead."""


# --------------------------------------------------------------------------
# probing
# --------------------------------------------------------------------------
def _rate(text: str | None) -> float:
    try:
        num, _, den = str(text or "0/1").partition("/")
        return float(num) / float(den or 1) if float(den or 1) else 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def probe_segment(path: Path) -> dict[str, Any]:
    proc = ac.run_cmd(["ffprobe", "-v", "error", "-print_format", "json",
                       "-show_format", "-show_streams", str(path)], timeout=120)
    if proc.returncode != 0:
        raise ConcatFallback(f"ffprobe failed on {path.name}: "
                             f"{(proc.stderr or '').strip()[-200:]}")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        raise ConcatFallback(f"{path.name} has no video stream")
    fmt_ms = int(round(float(data.get("format", {}).get("duration") or 0) * 1000))
    return {
        "path": str(path),
        "name": path.name,
        "stream_count": len(streams),
        "container_ms": fmt_ms,
        "video": {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "pix_fmt": video.get("pix_fmt"),
            "profile": video.get("profile"),
            "level": video.get("level"),
            "fps": round(_rate(video.get("r_frame_rate")), 3),
            "time_base": video.get("time_base"),
            "duration_ms": int(round(float(video.get("duration") or 0) * 1000)) or fmt_ms,
        },
        "audio": None if audio is None else {
            "codec": audio.get("codec_name"),
            "sample_rate": int(audio.get("sample_rate") or 0),
            "channels": int(audio.get("channels") or 0),
            "duration_ms": int(round(float(audio.get("duration") or 0) * 1000)) or fmt_ms,
        },
    }


def check_segments(specs: list[dict[str, Any]], cfg: dict[str, Any],
                   *, av_tolerance_ms: int = 80) -> list[str]:
    """Return human-readable reasons why stream-copy concat would be unsafe."""
    problems: list[str] = []
    for spec in specs:
        v, a = spec["video"], spec["audio"]
        name = spec["name"]
        if spec["stream_count"] != 2:
            problems.append(f"{name}: {spec['stream_count']} streams (need video+audio)")
        if v["codec"] != "h264":
            problems.append(f"{name}: video codec {v['codec']} != h264")
        if (v["width"], v["height"]) != (int(cfg["width"]), int(cfg["height"])):
            problems.append(f"{name}: {v['width']}x{v['height']} != "
                            f"{cfg['width']}x{cfg['height']}")
        if v["pix_fmt"] != "yuv420p":
            problems.append(f"{name}: pix_fmt {v['pix_fmt']} != yuv420p")
        if a is None:
            problems.append(f"{name}: no audio stream")
            continue
        if a["codec"] != "aac":
            problems.append(f"{name}: audio codec {a['codec']} != aac")
        if a["sample_rate"] != SAMPLE_RATE:
            problems.append(f"{name}: sample rate {a['sample_rate']} != {SAMPLE_RATE}")
        if a["channels"] != CHANNELS:
            problems.append(f"{name}: {a['channels']} channels != {CHANNELS}")
        delta = abs(v["duration_ms"] - a["duration_ms"])
        if delta > av_tolerance_ms:
            problems.append(f"{name}: A/V duration delta {delta} ms > {av_tolerance_ms} ms")
    bases = {spec["video"].get("time_base") for spec in specs}
    if len(bases) > 1:
        problems.append(f"mixed video time bases {sorted(bases)}; concat copy would "
                        "misplace timestamps")
    return problems


# --------------------------------------------------------------------------
# segment preparation (video copied, audio rebuilt)
# --------------------------------------------------------------------------
def _audio_format() -> str:
    return (f"aresample={SAMPLE_RATE},"
            "aformat=sample_fmts=fltp:channel_layouts=stereo")


def make_intro_segment(*, intro: Path, source: Path | None, bed: dict[str, Any],
                       intro_ms: int, out: Path, cfg: dict[str, Any],
                       log_path: Path) -> Path:
    """Copy the intro video; mix the source bed under the narration if enabled.

    The audio is trimmed to the *video* stream duration, so the segment never
    carries a dangling audio tail into the concat.
    """
    video_ms = probe_segment(intro)["video"]["duration_ms"] or intro_ms
    dur = video_ms / 1000.0
    if not (bed.get("enabled") and source is not None):
        cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(intro),
               "-map", "0:v:0", "-map", "0:a:0", "-c", "copy",
               "-t", f"{dur:.3f}", "-video_track_timescale", VIDEO_TIMESCALE,
               "-sn", "-dn", "-map_chapters", "-1",
               "-movflags", "+faststart", "-avoid_negative_ts", "make_zero",
               str(out)]
        proc = ac.run_cmd(cmd, timeout=600, log_path=log_path)
        if proc.returncode != 0:
            raise ConcatFallback(f"intro remux failed: {(proc.stderr or '')[-400:]}")
        return out
    bed_start = bed["start_ms"] / 1000.0
    bed_len = bed["duration_ms"] / 1000.0
    fade_out = min(bed["fade_out_ms"] / 1000.0, max(dur - 0.1, 0.0))
    graph = (
        f"[0:a]{_audio_format()},apad,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[na];"
        f"[1:a]{_audio_format()},apad,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
        f"volume={bed['volume']},afade=t=out:st={max(dur - fade_out, 0):.3f}:"
        f"d={fade_out:.3f}[bd];"
        "[na][bd]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
    )
    cmd = ["ffmpeg", "-hide_banner", "-y",
           "-i", str(intro),
           "-ss", f"{bed_start:.3f}", "-t", f"{bed_len:.3f}", "-i", str(source),
           "-filter_complex", graph,
           "-map", "0:v:0", "-map", "[aout]",
           "-c:v", "copy", "-video_track_timescale", VIDEO_TIMESCALE,
           "-c:a", "aac", "-b:a", cfg["audio_bitrate"],
           "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
           "-t", f"{dur:.3f}",
           "-sn", "-dn", "-map_chapters", "-1", "-movflags", "+faststart",
           "-avoid_negative_ts", "make_zero", str(out)]
    proc = ac.run_cmd(cmd, timeout=600, log_path=log_path)
    if proc.returncode != 0:
        raise ConcatFallback(f"intro segment failed: {(proc.stderr or '')[-400:]}")
    return out


def make_clip_segment(*, clip: Path, out: Path, cfg: dict[str, Any],
                      fade_in: bool, fade_out: bool, duration_ms: int,
                      log_path: Path) -> Path:
    """Copy the clip's video packets; re-encode audio only for the joins."""
    fade = int(cfg["fade_ms"]) / 1000.0
    dur = duration_ms / 1000.0
    filters: list[str] = []
    if fade_in:
        filters.append(f"afade=t=in:st=0:d={fade:.3f}")
    if fade_out:
        filters.append(f"afade=t=out:st={max(dur - fade, 0):.3f}:d={fade:.3f}")
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(clip),
           "-map", "0:v:0", "-map", "0:a:0",
           "-c:v", "copy", "-video_track_timescale", VIDEO_TIMESCALE,
           "-c:a", "aac", "-b:a", cfg["audio_bitrate"],
           "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
           "-t", f"{dur:.3f}",
           "-sn", "-dn", "-map_chapters", "-1", "-movflags", "+faststart",
           "-avoid_negative_ts", "make_zero"]
    if filters:
        cmd += ["-af", ",".join(filters)]
    cmd.append(str(out))
    proc = ac.run_cmd(cmd, timeout=1800, log_path=log_path)
    if proc.returncode != 0:
        raise ConcatFallback(f"clip segment failed: {(proc.stderr or '')[-400:]}")
    return out


def make_card_segment(*, png: Path, out: Path, transition_ms: int,
                      cfg: dict[str, Any], log_path: Path) -> Path:
    """Encode the title card as a 60 fps segment with silent AAC."""
    fps = int(cfg["fps"])
    dur = transition_ms / 1000.0
    frames = max(1, round(dur * fps))
    fade = min(int(cfg["card_fade_ms"]) / 1000.0, dur / 2)
    vf = (f"fps={fps},scale={int(cfg['width'])}:{int(cfg['height'])}:"
          f"force_original_aspect_ratio=decrease,"
          f"pad={int(cfg['width'])}:{int(cfg['height'])}:(ow-iw)/2:(oh-ih)/2,"
          f"setsar=1,format=yuv420p,"
          f"fade=t=in:st=0:d={fade:.3f},"
          f"fade=t=out:st={max(dur - fade, 0):.3f}:d={fade:.3f}")
    cmd = ["ffmpeg", "-hide_banner", "-y",
           "-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(png),
           "-f", "lavfi", "-t", f"{dur:.3f}",
           "-i", f"anullsrc=r={SAMPLE_RATE}:cl=stereo",
           "-map", "0:v:0", "-map", "1:a:0",
           "-vf", vf,
           "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]),
           "-preset", "slow", "-r", str(fps), "-frames:v", str(frames),
           "-video_track_timescale", VIDEO_TIMESCALE,
           "-c:a", "aac", "-b:a", cfg["audio_bitrate"],
           "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
           "-t", f"{dur:.3f}", "-shortest",
           "-sn", "-dn", "-movflags", "+faststart",
           "-avoid_negative_ts", "make_zero", str(out)]
    proc = ac.run_cmd(cmd, timeout=600, log_path=log_path)
    if proc.returncode != 0:
        raise ConcatFallback(f"card segment failed: {(proc.stderr or '')[-400:]}")
    return out


# --------------------------------------------------------------------------
# concat + verification
# --------------------------------------------------------------------------
def write_concat_list(segments: list[Path], path: Path) -> Path:
    lines = []
    for segment in segments:
        text = segment.resolve().as_posix()
        if "'" in text:
            text = text.replace("'", "'\\''")
        lines.append(f"file '{text}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_concat(*, list_path: Path, out: Path, cfg: dict[str, Any],
               reencode: bool, log_path: Path) -> list[str]:
    cmd = ["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0",
           "-i", str(list_path), "-map", "0:v:0", "-map", "0:a:0"]
    if reencode:
        cmd += ["-vf", f"fps={int(cfg['fps'])},format=yuv420p",
                "-af", f"{_audio_format()},asetpts=PTS-STARTPTS",
                "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]),
                "-preset", "slow", "-r", str(int(cfg["fps"])),
                "-c:a", "aac", "-b:a", cfg["audio_bitrate"],
                "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS)]
    else:
        cmd += ["-c", "copy"]
    cmd += ["-sn", "-dn", "-map_chapters", "-1", "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero", str(out)]
    proc = ac.run_cmd(cmd, timeout=7200, log_path=log_path)
    if proc.returncode != 0:
        raise ConcatFallback(f"concat failed: {(proc.stderr or '')[-500:]}")
    return cmd


def decode_joins(path: Path, joins_ms: list[int], *, window_s: float = 3.0,
                 timeout: int = 900) -> list[str]:
    """Decode a few seconds around each join; any stderr line is a red flag."""
    errors: list[str] = []
    for join in joins_ms:
        start = max(0.0, join / 1000.0 - window_s)
        length = window_s * 2
        proc = ac.run_cmd(["ffmpeg", "-hide_banner", "-v", "error",
                           "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
                           "-i", str(path), "-f", "null", "-"], timeout=timeout)
        text = (proc.stderr or "").strip()
        if proc.returncode != 0 or text:
            errors.append(f"join {join} ms: {text[-300:] or f'exit {proc.returncode}'}")
    return errors


def verify_concat_assembly(path: Path, *, expected_ms: int, intro_ms: int,
                           joins_ms: list[int], cfg: dict[str, Any],
                           expected_errors: list[str] | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    exists = path.exists() and path.stat().st_size > 0
    add("file_exists", exists, str(path) if exists else "missing or empty")
    if not exists:
        return {"passed": False, "checks": checks}

    spec = probe_segment(path)
    v, a = spec["video"], spec["audio"] or {}
    add("probe", True, "ffprobe parsed")
    add("only_av_streams", spec["stream_count"] == 2,
        f"{spec['stream_count']} streams")
    add("video_codec", v["codec"] == "h264", v["codec"])
    add("audio_codec", a.get("codec") == "aac", a.get("codec", "none"))
    add("resolution", (v["width"], v["height"]) ==
        (int(cfg["width"]), int(cfg["height"])), f"{v['width']}x{v['height']}")
    add("duration",
        abs(spec["container_ms"] - expected_ms) <= int(cfg["duration_tolerance_ms"]),
        f"actual {spec['container_ms']} ms vs expected {expected_ms} ms "
        f"(delta {spec['container_ms'] - expected_ms:+d})")
    delta = abs(v["duration_ms"] - int(a.get("duration_ms") or 0))
    add("av_duration_equal", bool(a) and delta <= 80,
        f"video {v['duration_ms']} ms vs audio {a.get('duration_ms')} ms (delta {delta})")
    add("fps", abs(v["fps"] - float(cfg["fps"])) <= 0.2,
        f"{v['fps']:.3f} fps, expected {cfg['fps']}")
    add("intro_duration", int(cfg["min_intro_ms"]) <= intro_ms <= int(cfg["max_intro_ms"]),
        f"{intro_ms} ms")
    if expected_errors is None:
        expected_errors = decode_joins(path, joins_ms)
    add("joins_decode", not expected_errors,
        "clean" if not expected_errors else " | ".join(expected_errors)[:500])
    return {"passed": all(c["ok"] for c in checks), "checks": checks,
            "actual_duration_ms": spec["container_ms"],
            "video_fps": v["fps"], "spec": spec}


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------
def build_concat_assembly(*, intro: Path, source: Path | None, bed: dict[str, Any],
                          clips: list[dict[str, Any]], card_png: Path,
                          intro_ms: int, transition_ms: int, tmp_out: Path,
                          work_dir: Path, cfg: dict[str, Any], mode: str,
                          log_path: Path) -> dict[str, Any]:
    """Prepare segments, join them, and verify.  Raises ConcatFallback."""
    fps = int(cfg["fps"])
    segments_dir = work_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    seg_log = log_path

    intro_seg = make_intro_segment(
        intro=intro, source=source, bed=bed, intro_ms=intro_ms,
        out=segments_dir / "intro.seg.mp4", cfg=cfg, log_path=seg_log)
    paths: list[Path] = [intro_seg]
    kinds: list[dict[str, Any]] = [{"kind": "intro", "path": intro_seg}]

    for index, clip in enumerate(clips):
        clip_path = resolve_clip(clip)
        spec = probe_segment(clip_path)
        seg = make_clip_segment(
            clip=clip_path, out=segments_dir / f"clip-{clip['index']:02d}.seg.mp4",
            cfg=cfg, fade_in=index > 0, fade_out=index < len(clips) - 1,
            duration_ms=spec["video"]["duration_ms"], log_path=seg_log)
        paths.append(seg)
        kinds.append({"kind": "clip", "clip_index": clip["index"], "path": seg})
        if index < len(clips) - 1 and transition_ms > 0:
            card = make_card_segment(
                png=card_png, out=segments_dir / f"transition-{index + 1:02d}.mp4",
                transition_ms=transition_ms, cfg=cfg, log_path=seg_log)
            paths.append(card)
            kinds.append({"kind": "transition", "path": card})

    specs = [probe_segment(p) for p in paths]
    problems = check_segments(specs, cfg)
    if problems:
        raise ConcatFallback("; ".join(problems))

    list_path = write_concat_list(paths, work_dir / "concat.txt")
    joins: list[int] = []
    offset = 0
    for spec in specs[:-1]:
        offset += spec["container_ms"]
        joins.append(offset)

    used = "copy"
    copy_log = work_dir / "assembly.concat.ffmpeg.log"
    try:
        run_concat(list_path=list_path, out=tmp_out, cfg=cfg, reencode=False,
                   log_path=copy_log)
    except ConcatFallback:
        if mode == "copy":
            raise
        used = "reencode"
        ac.RUN.log("stream copy join failed; re-encoding through the concat demuxer")
        run_concat(list_path=list_path, out=tmp_out, cfg=cfg, reencode=True,
                   log_path=copy_log)

    joins_errors = decode_joins(tmp_out, joins)
    if joins_errors and used == "copy" and mode == "auto":
        ac.RUN.log("copy join produced decode errors; retrying with a bounded re-encode")
        used = "reencode"
        run_concat(list_path=list_path, out=tmp_out, cfg=cfg, reencode=True,
                   log_path=copy_log)
        joins_errors = decode_joins(tmp_out, joins)

    acceptance = verify_concat_assembly(
        tmp_out, expected_ms=int(cfg["expected_ms"]), intro_ms=intro_ms,
        joins_ms=joins, cfg=cfg, expected_errors=joins_errors)
    return {
        "mode": used,
        "segments": kinds,
        "specs": specs,
        "joins_ms": joins,
        "concat_list": list_path,
        "ffmpeg_log": copy_log,
        "acceptance": acceptance,
        "segment_paths": paths,
        "fps": fps,
    }


def resolve_clip(clip: dict[str, Any]) -> Path:
    path = Path(str(clip.get("path")))
    return path if path.is_absolute() else (ac.ROOT / path)


def cleanup_segments(info: dict[str, Any]) -> None:
    for path in info.get("segment_paths", []):
        try:
            Path(path).unlink()
        except OSError:
            pass
    for parent in {Path(p).parent for p in info.get("segment_paths", [])}:
        try:
            parent.rmdir()
        except OSError:
            pass
