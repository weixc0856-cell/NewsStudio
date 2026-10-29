"""Assemble the standalone intro, accepted highlights, and a short transition.

Structure (16:9 horizontal reel):

    片头 (3-5 s, HTML picture + CosyVoice voice-over)
      -> highlight-01 (already accepted)
      -> title-card transition (0.3-0.8 s, audio faded)
      -> highlight-02 (already accepted)

Why this is not a plain MP4 concat: the accepted clips already carry burned-in
subtitles, so concatenating them and burning a merged subtitle file again would
double-render text. This script re-reads the same source intervals, inserts the
intro and the title card, rebases every clip's cues onto the final timeline, and
burns one merged ASS during a single QSV encode.

Usage:
    uv run python scripts/assemble_highlights.py --video-id c88l8daXiv4
    uv run python scripts/assemble_highlights.py --result clips/<id>/result.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_clip as ac  # noqa: E402
import concat_assembly as ca  # noqa: E402
import resource_manager as rm  # noqa: E402

SCHEMA_VERSION = 1

DEFAULTS: dict[str, Any] = {
    "transition_ms": 300,    # pure black gap between clips (no title card)
    "min_transition_ms": 100,
    "max_transition_ms": 800,
    "fade_ms": 200,          # audio fade at a clip boundary (dip-to-black partner)
    "video_fade_ms": 150,    # clip tail/head fade to/from black
    "audio_fade_ms": 200,    # audio fade at the same boundary
    "card_fade_ms": 100,     # legacy: fade inside the black fallback image
    "margin_v": 100,
    "qsv_quality": 19,
    "audio_bitrate": "160k",
    "audio_sample_rate": 48000,
    "width": 1920,
    "height": 1080,
    "fps": 60,
    "duration_tolerance_ms": 1500,
    "min_intro_ms": 10_000,
    "max_intro_ms": 20_000,
    "enforce_intro_window": False,   # 10-20 s is advisory, not a hard gate
}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (ac.ROOT / p)


def rel(path: Path) -> str:
    return ac.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def human_duration(ms: int) -> str:
    """Rounded up so 282.431 s reads as 4m43s (same convention as merge)."""
    total_s = math.ceil(ms / 1000)
    m, s = divmod(total_s, 60)
    return f"{m}m{s:02d}s"


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------
def load_inputs(result_path: Path, intro_arg: str | None = None
                ) -> tuple[dict[str, Any], list[dict[str, Any]], Path, dict[str, Any]]:
    data = json.loads(result_path.read_text(encoding="utf-8"))
    if data.get("status") not in ("SUCCESS", "PARTIAL"):
        raise RuntimeError(f"result status is {data.get('status')}; nothing to assemble")
    clips = data.get("clips", [])
    accepted = [c for c in clips if c.get("acceptance", {}).get("passed")]
    if not accepted:
        raise RuntimeError("no accepted clips in result.json")
    if len(accepted) != len(clips):
        raise RuntimeError(f"{len(clips) - len(accepted)} clip(s) did not pass acceptance")
    for clip in accepted:
        if not clip.get("path") or not resolve(clip["path"]).exists():
            raise RuntimeError(f"clip {clip.get('index')} file is missing: {clip.get('path')}")
        if not clip.get("srt") or not resolve(clip["srt"]).exists():
            raise RuntimeError(f"clip {clip.get('index')} SRT is missing: {clip.get('srt')}")
        if int(clip.get("duration_ms", 0)) <= 0:
            raise RuntimeError(f"clip {clip.get('index')} has no duration")
    accepted.sort(key=lambda c: c["start_ms"])

    out_dir = result_path.parent
    intro_meta: dict[str, Any] = {}
    intro_json = out_dir / "intro" / "intro.json"
    if intro_json.exists():
        intro_meta = json.loads(intro_json.read_text(encoding="utf-8"))

    if intro_arg:
        intro_path = resolve(intro_arg)
    else:
        declared = (data.get("intro") or {}).get("path")
        if declared:
            intro_path = resolve(declared)
        elif intro_meta.get("path"):
            intro_path = resolve(intro_meta["path"])
        else:
            intro_path = out_dir / "intro" / "intro.mp4"
    if not intro_path.exists():
        raise RuntimeError(f"intro not found: {intro_path} (run generate_intro.py first)")
    if not intro_meta:
        info = ac.probe_source(intro_path)
        intro_meta = {"path": rel(intro_path), "duration_ms": info["duration_ms"],
                      "status": "UNKNOWN", "acceptance": {}}
    return data, accepted, intro_path, intro_meta


# --------------------------------------------------------------------------
# timeline (pure, unit-tested)
# --------------------------------------------------------------------------
def build_timeline(clips: list[dict[str, Any]], intro_ms: int, transition_ms: int
                   ) -> tuple[list[dict[str, Any]], int, list[int]]:
    if intro_ms <= 0:
        raise ValueError("intro duration must be positive")
    if transition_ms < 0:
        raise ValueError("transition duration must be >= 0")
    segments: list[dict[str, Any]] = [{
        "kind": "intro",
        "label": "片头",
        "offset_ms": 0,
        "duration_ms": intro_ms,
        "end_ms": intro_ms,
    }]
    offset = intro_ms
    for index, clip in enumerate(clips):
        segments.append({
            "kind": "clip",
            "label": f"高光片段 {clip['index']:02d}",
            "clip_index": clip["index"],
            "title": clip.get("title", ""),
            "source_start_ms": clip["start_ms"],
            "source_end_ms": clip["start_ms"] + clip["duration_ms"],
            "offset_ms": offset,
            "duration_ms": clip["duration_ms"],
            "end_ms": offset + clip["duration_ms"],
        })
        offset += clip["duration_ms"]
        if index < len(clips) - 1 and transition_ms > 0:
            segments.append({
                "kind": "transition",
                "label": f"黑场 {clip['index']:02d}→{clips[index + 1]['index']:02d}",
                "offset_ms": offset,
                "duration_ms": transition_ms,
                "end_ms": offset + transition_ms,
            })
            offset += transition_ms
    gaps: list[int] = []
    for prev, cur in zip(clips, clips[1:]):
        gap = cur["start_ms"] - (prev["start_ms"] + prev["duration_ms"])
        if gap < 0:
            raise ValueError(f"clips {prev['index']} and {cur['index']} overlap")
        gaps.append(gap)
    return segments, offset, gaps


def clip_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in segments if s["kind"] == "clip"]


def subtitle_rows(clips: list[dict[str, Any]], intro_ms: int, transition_ms: int
                  ) -> tuple[list[tuple[int, int, str, str]], list[dict[str, Any]], int]:
    rows: list[tuple[int, int, str, str]] = []
    segments: list[dict[str, Any]] = []
    offset = intro_ms
    for index, clip in enumerate(clips):
        cues, errors = ac.parse_bilingual_srt(resolve(clip["srt"]))
        if errors:
            raise RuntimeError(f"clip {clip['index']} SRT is invalid: {errors[:2]}")
        local_max = max((c.end for c in cues), default=0)
        if local_max > clip["duration_ms"]:
            raise RuntimeError(f"clip {clip['index']} subtitles overflow its duration")
        for cue in cues:
            rows.append((cue.start + offset, cue.end + offset, cue.top, cue.bottom))
        segments.append({
            "clip_index": clip["index"],
            "offset_ms": offset,
            "cues": len(cues),
            "max_end_ms": local_max + offset,
        })
        offset += clip["duration_ms"]
        if index < len(clips) - 1:
            offset += transition_ms
    if any(rows[i][0] < rows[i - 1][0] for i in range(1, len(rows))):
        raise RuntimeError("merged subtitle rows are not chronological")
    if rows and max(r[1] for r in rows) > offset:
        raise RuntimeError("merged subtitles overflow the assembled duration")
    return rows, segments, offset


def source_windows(clips: list[dict[str, Any]]) -> tuple[list[tuple[float, float]], float]:
    """Clip intervals relative to the first clip's start, and seconds to read."""
    base = clips[0]["start_ms"]
    windows = [((c["start_ms"] - base) / 1000.0,
                (c["start_ms"] - base + c["duration_ms"]) / 1000.0) for c in clips]
    return windows, windows[-1][1]


# --------------------------------------------------------------------------
# filter graph (pure, unit-tested)
# --------------------------------------------------------------------------
def bed_plan(clips: list[dict[str, Any]], intro_ms: int) -> dict[str, Any]:
    """Pre-roll source audio under the intro, at ~15%, fading out over 0.4 s."""
    start = int(clips[0]["start_ms"])
    bed_start = max(0, start - intro_ms)
    bed_len = min(intro_ms, start)
    if bed_len < 300:
        return {"enabled": False, "start_ms": bed_start, "duration_ms": bed_len,
                "volume": 0.15, "fade_out_ms": 400}
    return {"enabled": True, "start_ms": bed_start, "duration_ms": bed_len,
            "volume": 0.15, "fade_out_ms": 400}


def build_filter_complex(*, clips: list[dict[str, Any]], intro_ms: int, transition_ms: int,
                         ass_path: Path, cfg: dict[str, Any],
                         bed: bool = False) -> str:
    """Return the concat graph: [0:v]/[1:v]/[2:v] -> [v], audio -> [aout].

    Input 0 = intro.mp4, input 1 = source video, input 2 = transition PNG.
    """
    n = len(clips)
    windows, _ = source_windows(clips)
    fade = min(int(cfg["fade_ms"]), max(int(c["duration_ms"]) for c in clips) // 2)
    card_fade = min(int(cfg["card_fade_ms"]), max(transition_ms // 2, 1))
    parts: list[str] = []

    # ---- video ----
    parts.append(
        f"[0:v]fps={cfg['fps']},scale={cfg['width']}:{cfg['height']}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={cfg['width']}:{cfg['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
        f"trim=duration={intro_ms / 1000:.3f},format=yuv420p,"
        f"fps={cfg['fps']},settb=AVTB,setpts=PTS-STARTPTS[vi0]"
    )
    parts.append(f"[1:v]split={n}" + "".join(f"[bv{i}]" for i in range(n)))
    for i, (start, end) in enumerate(windows):
        dur = end - start
        parts.append(
            f"[bv{i}]select='between(t,{start:.3f},{end:.3f})',setpts=PTS-STARTPTS,"
            f"scale={cfg['width']}:{cfg['height']}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={cfg['width']}:{cfg['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
            f"trim=duration={dur:.3f},format=yuv420p,"
            f"fps={cfg['fps']},settb=AVTB,setpts=PTS-STARTPTS[vi{i + 1}]"
        )
    if n > 1 and transition_ms > 0:
        cards = n - 1
        parts.append(f"[2:v]split={cards}" + "".join(f"[cv{i}]" for i in range(cards)))
        for i in range(cards):
            parts.append(
                f"[cv{i}]fps={cfg['fps']},scale={cfg['width']}:{cfg['height']}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={cfg['width']}:{cfg['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                f"trim=duration={transition_ms / 1000:.3f},"
                f"fade=t=in:st=0:d={card_fade / 1000:.3f},"
                f"fade=t=out:st={(transition_ms - card_fade) / 1000:.3f}:"
                f"d={card_fade / 1000:.3f},format=yuv420p,"
                f"fps={cfg['fps']},settb=AVTB,setpts=PTS-STARTPTS[vc{i}]"
            )

    v_pads = ["[vi0]"]
    for i in range(n):
        v_pads.append(f"[vi{i + 1}]")
        if i < n - 1 and transition_ms > 0:
            v_pads.append(f"[vc{i}]")
    parts.append("".join(v_pads) + f"concat=n={len(v_pads)}:v=1:a=0[vcat]")
    parts.append(f"[vcat]ass={ac.escape_filter_path(ass_path)}[v]")

    # ---- audio ----
    intro_dur = intro_ms / 1000.0
    parts.append(
        f"[0:a]aresample={cfg['audio_sample_rate']},"
        f"aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
        f"atrim=0:{intro_dur:.3f},aresample={cfg['audio_sample_rate']},"
        f"asetpts=PTS-STARTPTS[ai0]"
    )
    if bed:
        parts.append(
            f"[3:a]aresample={cfg['audio_sample_rate']},"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
            f"atrim=0:{intro_dur:.3f},volume=0.15,"
            f"afade=t=out:st={max(intro_dur - 0.400, 0):.3f}:d=0.400,"
            f"aresample={cfg['audio_sample_rate']},asetpts=PTS-STARTPTS[bed]"
        )
        parts.append(
            "[ai0][bed]amix=inputs=2:duration=first:dropout_transition=0:"
            "normalize=0[ai0mix]"
        )
        intro_pad = "[ai0mix]"
    else:
        intro_pad = "[ai0]"
    parts.append(f"[1:a]asplit={n}" + "".join(f"[ba{i}]" for i in range(n)))
    for i, (start, end) in enumerate(windows):
        dur = end - start
        chain = (f"[ba{i}]aselect='between(t,{start:.3f},{end:.3f})',"
                 f"aresample={cfg['audio_sample_rate']},"
                 f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"asetpts=PTS-STARTPTS")
        if i > 0:
            chain += f",afade=t=in:st=0:d={fade / 1000:.3f}"
        if i < n - 1:
            chain += (f",afade=t=out:st={max(dur - fade / 1000, 0):.3f}:"
                      f"d={fade / 1000:.3f}")
        parts.append(chain + f"[ai{i + 1}]")

    a_pads = [intro_pad]
    if n > 1 and transition_ms > 0:
        cards = n - 1
        parts.append(
            f"anullsrc=r={cfg['audio_sample_rate']}:cl=stereo,"
            f"atrim=duration={transition_ms / 1000:.3f},"
            f"aresample={cfg['audio_sample_rate']},"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"asetpts=PTS-STARTPTS,asplit={cards}" + "".join(f"[ac{i}]" for i in range(cards))
        )
    for i in range(n):
        a_pads.append(f"[ai{i + 1}]")
        if i < n - 1 and transition_ms > 0:
            a_pads.append(f"[ac{i}]")
    parts.append("".join(a_pads) + f"concat=n={len(a_pads)}:v=0:a=1[aout]")
    return ";".join(parts)


def build_ffmpeg_cmd(*, intro: Path, source: Path, card: Path, out: Path,
                     clips: list[dict[str, Any]], intro_ms: int, transition_ms: int,
                     ass_path: Path, cfg: dict[str, Any],
                     bed: dict[str, Any] | None = None) -> list[str]:
    _, read_s = source_windows(clips)
    base_s = clips[0]["start_ms"] / 1000.0
    bed_on = bool(bed and bed.get("enabled"))
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(intro),
        "-ss", f"{base_s:.3f}", "-t", f"{read_s + 0.5:.3f}", "-i", str(source),
        "-loop", "1", "-framerate", str(cfg["fps"]),
        "-t", f"{transition_ms / 1000:.3f}", "-i", str(card),
    ]
    if bed_on:
        cmd += ["-ss", f"{bed['start_ms'] / 1000:.3f}",
                "-t", f"{bed['duration_ms'] / 1000:.3f}", "-i", str(source)]
    return cmd + [
        "-map_chapters", "-1",
        "-filter_complex",
        build_filter_complex(clips=clips, intro_ms=intro_ms, transition_ms=transition_ms,
                             ass_path=ass_path, cfg=cfg, bed=bed_on),
        "-map", "[v]", "-map", "[aout]",
        "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]), "-preset", "slow",
        "-r", str(cfg["fps"]),
        "-c:a", "aac", "-b:a", cfg["audio_bitrate"],
        "-ar", str(cfg["audio_sample_rate"]), "-ac", "2",
        "-sn", "-dn", "-movflags", "+faststart", "-avoid_negative_ts", "make_zero",
        str(out),
    ]


# --------------------------------------------------------------------------
# acceptance
# --------------------------------------------------------------------------
def prune_outputs(out_dir: Path, merged: Path, data: dict[str, Any]) -> list[str]:
    """After a successful assembly keep only the whitelisted delivery assets."""
    removed: list[str] = []
    final_dir = out_dir / "final"
    keep = {merged.resolve()}
    for clip in data.get("clips", []):
        if clip.get("path"):
            keep.add(resolve(clip["path"]).resolve())
    for path in final_dir.glob("*.mp4"):
        if path.resolve() in keep:
            continue
        try:
            path.unlink()
            removed.append(rel(path))
        except OSError:
            pass
    work = out_dir / "work"
    segments = work / "segments"
    if segments.is_dir():
        shutil.rmtree(segments, ignore_errors=True)
        removed.append(rel(segments))
    for pattern in ("*.tmp.mp4", "*.concat.txt"):
        for path in work.glob(pattern):
            try:
                path.unlink()
                removed.append(rel(path))
            except OSError:
                pass
    for name in ("concat.txt", "black.png", "transition.png"):
        path = work / name
        if path.exists():
            try:
                path.unlink()
                removed.append(rel(path))
            except OSError:
                pass
    return removed


def verify_assembly(path: Path, total_ms: int, rows: list[tuple[int, int, str, str]],
                    intro_ms: int, cfg: dict[str, Any]) -> dict[str, Any]:
    clip = {"start_ms": 0, "end_ms": total_ms, "duration_ms": total_ms}
    base_cfg = {
        "duration_tolerance_ms": cfg["duration_tolerance_ms"],
        "video_codec": "h264",
        "audio_codec": "aac",
    }
    result = ac.verify_clip(path, clip, rows, base_cfg)
    checks = result["checks"]

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    intro_ok = cfg["min_intro_ms"] <= intro_ms <= cfg["max_intro_ms"]
    advisory = not cfg.get("enforce_intro_window", True)
    add("intro_duration", intro_ok or advisory,
        f"{intro_ms} ms, window [{cfg['min_intro_ms']}, {cfg['max_intro_ms']}]"
        + (" (advisory)" if advisory else ""))

    min_start = min((r[0] for r in rows), default=intro_ms)
    add("subtitles_after_intro", min_start >= intro_ms,
        f"first cue at {min_start} ms, intro ends at {intro_ms} ms")
    ordered = all(rows[i][0] >= rows[i - 1][0] for i in range(1, len(rows)))
    add("subtitles_chronological", ordered, f"{len(rows)} cues")

    proc = ac.run_cmd(["ffprobe", "-v", "error", "-print_format", "json",
                       "-show_streams", str(path)], timeout=60)
    width = height = None
    if proc.returncode == 0:
        for stream in json.loads(proc.stdout).get("streams", []):
            if stream.get("codec_type") == "video":
                width, height = stream.get("width"), stream.get("height")
    add("resolution", (width, height) == (cfg["width"], cfg["height"]),
        f"{width}x{height}")

    return {"passed": all(c["ok"] for c in checks), "checks": checks,
            "actual_duration_ms": result.get("actual_duration_ms")}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Assemble intro + highlights + transition")
    ap.add_argument("--result", default=None, help="clips/<id>/result.json")
    ap.add_argument("--video-id", default=None, help="alternative to --result")
    ap.add_argument("--source", default=None, help="source video (default: result.json)")
    ap.add_argument("--intro", default=None, help="intro MP4 (default: clips/<id>/intro/intro.mp4)")
    ap.add_argument("--out", default=None,
                    help="default clips/<id>/final/<id>.highlights-merged.mp4")
    ap.add_argument("--work-dir", default=None, help="default clips/<id>/work")
    ap.add_argument("--transition-ms", type=int, default=DEFAULTS["transition_ms"])
    ap.add_argument("--fade-ms", type=int, default=DEFAULTS["fade_ms"])
    ap.add_argument("--qsv-quality", type=int, default=DEFAULTS["qsv_quality"])
    ap.add_argument("--audio-bitrate", default=DEFAULTS["audio_bitrate"])
    ap.add_argument("--margin-v", type=int, default=DEFAULTS["margin_v"])
    ap.add_argument("--duration-tolerance-ms", type=int, default=DEFAULTS["duration_tolerance_ms"])
    ap.add_argument("--fps", type=int, default=DEFAULTS["fps"])
    ap.add_argument("--width", type=int, default=DEFAULTS["width"])
    ap.add_argument("--height", type=int, default=DEFAULTS["height"])
    ap.add_argument("--renderer", choices=("auto", "html", "drawtext"), default="auto")
    ap.add_argument("--browser", default=None)
    ap.add_argument("--mode", choices=("auto", "copy", "reencode", "filter"),
                    default="auto",
                    help="auto: concat stream-copy, fall back to bounded re-encode; "
                         "filter: legacy single filter_complex re-encode")
    ap.add_argument("--keep-segments", action="store_true",
                    help="keep the normalized segment MP4s in work/segments")
    return ap.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not (DEFAULTS["min_transition_ms"] <= args.transition_ms <= DEFAULTS["max_transition_ms"]):
        print("config error: transition-ms must be within "
              f"[{DEFAULTS['min_transition_ms']}, {DEFAULTS['max_transition_ms']}]",
              file=sys.stderr)
        return 2

    if args.result:
        result_path = resolve(args.result)
    elif args.video_id:
        result_path = ac.ROOT / "clips" / args.video_id / "result.json"
    else:
        print("config error: pass --result or --video-id", file=sys.stderr)
        return 2
    if not result_path.exists():
        print(f"result not found: {result_path}", file=sys.stderr)
        return 1
    out_dir = result_path.parent
    work_dir = resolve(args.work_dir) if args.work_dir else out_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    ac.RUN.log_path = out_dir / "assemble.log"
    ac.RUN.log(f"=== assemble_highlights {now_iso()} ===")
    try:
        rm.assert_quiet(context="assembly (QSV)")
    except rm.ResourceBusyError as exc:
        ac.RUN.log(f"resource check failed: {exc}")
        return 1
    ac.RUN.log("resource check: no model process alive, QSV window is exclusive")

    cfg: dict[str, Any] = {
        **DEFAULTS,
        "transition_ms": args.transition_ms,
        "fade_ms": args.fade_ms,
        "qsv_quality": args.qsv_quality,
        "audio_bitrate": args.audio_bitrate,
        "margin_v": args.margin_v,
        "duration_tolerance_ms": args.duration_tolerance_ms,
        "fps": args.fps,
        "width": args.width,
        "height": args.height,
    }

    try:
        data, clips, intro_path, intro_meta = load_inputs(result_path, args.intro)
    except RuntimeError as exc:
        ac.RUN.log(f"cannot assemble: {exc}")
        return 1

    try:
        intro_info = ac.probe_source(intro_path)
        intro_ms = int(intro_info["duration_ms"])
        if not (cfg["min_intro_ms"] <= intro_ms <= cfg["max_intro_ms"]):
            if cfg.get("enforce_intro_window", True):
                raise RuntimeError(f"intro is {intro_ms} ms, outside "
                                   f"[{cfg['min_intro_ms']}, {cfg['max_intro_ms']}]")
            ac.RUN.log(f"intro duration advisory: {intro_ms} ms outside "
                       f"[{cfg['min_intro_ms']}, {cfg['max_intro_ms']}]")
        segments, total_ms, gaps = build_timeline(clips, intro_ms, args.transition_ms)
        rows, subtitle_segments, subtitle_total = subtitle_rows(
            clips, intro_ms, args.transition_ms)
        if subtitle_total != total_ms:
            raise RuntimeError(f"subtitle duration {subtitle_total} != timeline {total_ms}")
        black_seg = next((s for s in segments if s["kind"] == "transition"), None)
    except Exception as exc:
        ac.RUN.log(f"assembly preparation failed: {exc}")
        return 1

    source: Path | None = None
    raw_source = Path(args.source) if args.source else data.get("source")
    if raw_source:
        candidate = resolve(raw_source)
        if candidate.exists():
            source = candidate
    if source is None:
        if args.mode == "filter":
            ac.RUN.log("source video missing; filter mode needs it")
            return 1
        ac.RUN.log("source video missing; concat mode continues without the intro bed")

    srt_path = work_dir / "assembly.srt"
    ass_path = work_dir / "assembly.ass"
    ac.write_srt([(s / 1000, e / 1000, top, bottom) for s, e, top, bottom in rows], srt_path)
    ac.write_ass([(s / 1000, e / 1000, top, bottom) for s, e, top, bottom in rows],
                 ass_path, margin_v=args.margin_v, top_only=False, font="Microsoft YaHei")

    card_info: dict[str, Any] = {"mode": "black", "html": None, "png": None}
    card_path: Path | None = None
    if black_seg is not None:
        card_path = work_dir / "black.png"
        black_cmd = ["ffmpeg", "-hide_banner", "-y", "-f", "lavfi",
                     "-i", f"color=c=black:s={cfg['width']}x{cfg['height']}",
                     "-frames:v", "1", str(card_path)]
        proc = ac.run_cmd(black_cmd, timeout=60)
        if proc.returncode != 0 or not card_path.exists():
            ac.RUN.log("could not create the black placeholder")
            return 1

    out_path = Path(args.out) if args.out else out_dir / "final" / (
        f"{data.get('video_id', out_dir.name)}.highlights-merged.mp4")
    if not out_path.is_absolute():
        out_path = resolve(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_dir = out_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = work_dir / "assembly.tmp.mp4"
    ffmpeg_log = work_dir / "assembly.ffmpeg.log"

    bed = bed_plan(clips, intro_ms)
    if source is None:
        bed = {**bed, "enabled": False}
    ac.RUN.log(f"assembling intro {intro_ms} ms + {len(clips)} clip(s) "
               f"+ {args.transition_ms} ms transition = {total_ms} ms")
    ac.RUN.log(f"intro bed: {'on' if bed['enabled'] else 'off'} "
               f"start {bed['start_ms']} ms, {bed['duration_ms']} ms, "
               f"volume {bed['volume']}, fade-out {bed['fade_out_ms']} ms")

    concat_info: dict[str, Any] | None = None
    if args.mode in ("auto", "copy", "reencode"):
        cfg["expected_ms"] = total_ms
        try:
            concat_info = ca.build_concat_assembly(
                intro=intro_path, source=source if bed["enabled"] else None,
                bed=bed, clips=clips, intro_ms=intro_ms,
                transition_ms=args.transition_ms, tmp_out=tmp_path,
                work_dir=work_dir, cfg=cfg, mode=args.mode, log_path=ffmpeg_log)
            acceptance = concat_info["acceptance"]
            ffmpeg_log = concat_info["ffmpeg_log"]
            ac.RUN.log(f"media path: concat demuxer ({concat_info['mode']}), "
                       f"{len(concat_info['segments'])} segment(s), joins at "
                       f"{concat_info['joins_ms']} ms")
        except ca.ConcatFallback as exc:
            ac.RUN.log(f"concat path unavailable ({exc}); using filter_complex fallback")
            concat_info = None

    if concat_info is None:
        cmd = build_ffmpeg_cmd(intro=intro_path, source=source, card=card_path,
                               out=tmp_path, clips=clips, intro_ms=intro_ms,
                               transition_ms=args.transition_ms, ass_path=ass_path,
                               cfg=cfg, bed=bed)
        proc = ac.run_cmd(cmd, timeout=7200, log_path=ffmpeg_log)
        if proc.returncode != 0:
            ac.RUN.log(f"ffmpeg failed: {proc.stderr.strip()[-800:]}")
            data["assembly"] = {
                "status": "FAILED",
                "error": f"ffmpeg exit {proc.returncode}",
                "expected_duration_ms": total_ms,
                "segments": segments,
                "acceptance": {"passed": False, "checks": []},
            }
            ac.write_json(result_path, data)
            return 1
        acceptance = verify_assembly(tmp_path, total_ms, rows, intro_ms, cfg)

    if acceptance["passed"]:
        os.replace(tmp_path, out_path)
        status, target = "SUCCESS", out_path
    else:
        target = quarantine_dir / out_path.name
        os.replace(tmp_path, target)
        status = "FAILED"
    if concat_info is not None and not args.keep_segments:
        ca.cleanup_segments(concat_info)
    if status == "SUCCESS":
        pruned = prune_outputs(out_dir, target, data)
        if pruned:
            ac.RUN.log(f"pruned {len(pruned)} intermediate file(s)")

    skipped = sum(gaps)
    assembly = {
        "schema_version": SCHEMA_VERSION,
        "video_id": data.get("video_id", out_dir.name),
        "status": status,
        "output": rel(target) if status == "SUCCESS" else None,
        "quarantined": None if status == "SUCCESS" else rel(target),
        "expected_duration_ms": total_ms,
        "actual_duration_ms": acceptance.get("actual_duration_ms"),
        "segments": segments,
        "bed": bed,
        "transition": {
            "type": "dip_to_black" if black_seg else "none",
            "duration_ms": args.transition_ms,
            "video_fade_ms": cfg["video_fade_ms"],
            "audio_fade_ms": cfg["audio_fade_ms"],
            "black": True,
            "title": None,
        },
        "intro": {
            "path": rel(intro_path),
            "duration_ms": intro_ms,
            "status": intro_meta.get("status"),
            "headline": (intro_meta.get("picture") or {}).get("headline"),
            "subtitle": (intro_meta.get("picture") or {}).get("subline"),
            "narration": (intro_meta.get("narration") or {}).get("text"),
            "animation": (intro_meta.get("picture") or {}).get("animation"),
            "template": intro_meta.get("template"),
            "copy_source": (intro_meta.get("copy") or {}).get("source"),
            "copy_model": (intro_meta.get("copy") or {}).get("model"),
        },
        "subtitle_segments": subtitle_segments,
        "gaps_ms": gaps,
        "skipped_ms": skipped,
        "skipped_human": human_duration(skipped) if skipped else "0m00s",
        "note": (f"合集非连续剪辑，中间跳过约 {human_duration(skipped)}（{skipped} ms）；"
                 f"片头为本地 Qwen 文案 + HTML 关键帧 + CosyVoice 配音，转场为 {args.transition_ms} ms 标题卡"
                 if gaps else "片段连续；片头 + 标题卡转场"),
        "subtitle_srt": rel(srt_path),
        "subtitle_ass": rel(ass_path),
        "manual_review": False,
        "target_platform": f"16:9 横屏 ({cfg['width']}x{cfg['height']}@{cfg['fps']}fps)",
        "acceptance": acceptance,
        "media_mode": (f"concat-{concat_info['mode']}" if concat_info else "filter"),
        "subtitle_mode": "burned_in_per_clip" if concat_info else "burned_merged",
        "concat": (None if concat_info is None else {
            "mode": concat_info["mode"],
            "segments": [{k: v for k, v in seg.items() if k != "path"}
                         for seg in concat_info["segments"]],
            "joins_ms": concat_info["joins_ms"],
            "list": rel(concat_info["concat_list"]),
        }),
        "ffmpeg_log": rel(ffmpeg_log),
        "generated_at": now_iso(),
    }
    data["assembly"] = assembly
    if "intro" not in data and intro_meta:
        # auto_clip rewrites result.json when it renders clips; restore the
        # intro block so the final metadata still points at the standalone card.
        data["intro"] = {**intro_meta, "manual_review": False,
                         "target_platform": assembly["target_platform"]}
    data["manual_review"] = False
    for clip in data.get("clips", []):
        clip.setdefault("video_id", data.get("video_id", out_dir.name))
        clip.setdefault("manual_review", False)
        clip.setdefault("target_platform", assembly["target_platform"])
    if "intro" in data:
        data["intro"].setdefault("manual_review", False)
    ac.write_json(result_path, data)

    failed = [c["name"] for c in acceptance["checks"] if not c["ok"]]
    ac.RUN.log(f"assembly status: {status} | expected {total_ms} ms / actual "
               f"{acceptance.get('actual_duration_ms')} ms | skipped {assembly['skipped_human']}")
    if failed:
        ac.RUN.log(f"failed checks: {failed}")
    if status == "SUCCESS":
        ac.RUN.log(f"final reel: {rel(target)}")
    return 0 if status == "SUCCESS" else 1


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
