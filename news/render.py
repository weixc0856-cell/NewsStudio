"""Deterministic FFmpeg renderer for the news pipeline.

Pipeline per episode:
  visual segment -> CFR MP4 (no audio)
  concat demuxer  -> one video track
  narration WAVs  -> per-segment padded WAVs -> concat -> one audio track
  final mux       -> burn ASS + loudnorm -> H.264/AAC MP4
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from . import capture, subs
from .schemas import Cue, write_json

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"
AUDIO_RATE = 48_000
AUDIO_BITRATE = "160k"
VIDEO_QUALITY = 19


def _run(cmd: list[str], *, cwd: Path, log: Path, timeout: float = 1800) -> subprocess.CompletedProcess:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        handle.write("\n$ " + " ".join(cmd) + "\n")
        handle.flush()
        proc = subprocess.run(cmd, cwd=str(cwd), stdout=handle, stderr=subprocess.STDOUT,
                              timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}); see {log}")
    return proc


def probe(path: str | Path) -> dict[str, Any]:
    cmd = [FFPROBE, "-v", "error", "-show_entries",
           "format=duration,size:stream=index,codec_type,codec_name,width,height,"
           "r_frame_rate,sample_rate,channels",
           "-of", "json", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(out.stdout or "{}")
    duration = float(data.get("format", {}).get("duration") or 0) * 1000
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "duration_ms": int(round(duration)),
        "size": int(data.get("format", {}).get("size") or 0),
        "video": video,
        "audio": audio,
        "streams": streams,
    }



def _scrim_filter() -> str:
    """A solid lower-third bar: readable over any news page or screenshot."""
    return "drawbox=x=0:y=ih-200:w=iw:h=200:color=black@0.82:t=fill"

def _encoder_args(encoder: str) -> list[str]:
    if encoder == "qsv":
        return ["-c:v", "h264_qsv", "-global_quality:v", str(VIDEO_QUALITY), "-preset", "slow"]
    return ["-c:v", "libx264", "-crf", "19", "-preset", "medium"]


def _motion_filter(motion: str, width: int, height: int, fps: int, frames: int) -> str:
    if motion == "static":
        return ""
    if motion == "zoom-out":
        z = "if(eq(on,1),1.08,max(zoom-0.0005,1.0))"
        return (f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d=1:s={width}x{height}:fps={fps}")
    if motion in ("pan-left", "pan-right"):
        expr = f"(iw-iw/zoom)*({1 if motion == 'pan-left' else 0}" \
               f"{'-' if motion == 'pan-left' else '+'}on/{max(1, frames)})"
        return (f"zoompan=z='1.06':x='{expr}':y='ih/2-(ih/zoom/2)'"
                f":d=1:s={width}x{height}:fps={fps}")
    return (f"zoompan=z='min(zoom+0.0005,1.08)':x='iw/2-(iw/zoom/2)'"
            f":y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps}")


def _visual_filter(seg: dict[str, Any], width: int, height: int, fps: int) -> str:
    seconds = seg["duration_ms"] / 1000.0
    frames = max(1, int(round(seconds * fps)))
    base = (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1")
    motion = _motion_filter(seg.get("motion") or "zoom-in", width, height, fps, frames)
    tail = f"fps={fps},format=yuv420p"
    return ",".join(part for part in (base, motion, tail) if part)


def render_visual_segment(seg: dict[str, Any], out: Path, work: Path, *,
                          width: int, height: int, fps: int, encoder: str,
                          log: Path) -> dict[str, Any]:
    seconds = seg["duration_ms"] / 1000.0
    if seg["type"] == "clip":
        source = Path(seg["video"])
        if not source.is_file():
            raise FileNotFoundError(f"clip not found: {source}")
        start = max(0, int(seg.get("video_in_ms") or 0)) / 1000.0
        vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
              f"fps={fps},format=yuv420p")
        cmd = [FFMPEG, "-hide_banner", "-y", "-stream_loop", "-1",
               "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{seconds:.3f}",
               "-vf", vf, *_encoder_args(encoder), "-an", "-r", str(fps),
               "-movflags", "+faststart", str(out)]
    else:
        image = Path(seg.get("image") or "")
        if not image.is_file():
            if seg["type"] in ("source_card", "quote"):
                image = work / f"card-{seg['id']}.png"
                capture.render_segment_card(seg, image, width=width, height=height,
                                            index=seg["id"], work_dir=work)
            else:
                raise FileNotFoundError(f"image not found: {image}")
        vf = _visual_filter(seg, width, height, fps)
        cmd = [FFMPEG, "-hide_banner", "-y", "-loop", "1", "-framerate", str(fps),
               "-i", str(image), "-t", f"{seconds:.3f}", "-vf", vf,
               *_encoder_args(encoder), "-an", "-r", str(fps),
               "-movflags", "+faststart", str(out)]
    _run(cmd, cwd=work, log=log)
    info = probe(out)
    if abs(info["duration_ms"] - seg["duration_ms"]) > 200:
        raise RuntimeError(f"{seg['id']}: segment duration {info['duration_ms']} ms "
                           f"!= declared {seg['duration_ms']} ms")
    return {"id": seg["id"], "duration_ms": info["duration_ms"], "file": str(out)}


def render_audio_segment(seg: dict[str, Any], out: Path, work: Path, *, log: Path) -> dict[str, Any]:
    seconds = seg["duration_ms"] / 1000.0
    wav = seg.get("narration_wav") or ""
    audio_filter = (f"aresample={AUDIO_RATE},apad=whole_dur={seconds:.3f},"
                    f"atrim=0:{seconds:.3f},"
                    f"aformat=sample_fmts=s16:channel_layouts=stereo")
    if wav and Path(wav).is_file():
        cmd = [FFMPEG, "-hide_banner", "-y", "-i", wav, "-af", audio_filter,
               "-t", f"{seconds:.3f}", "-ar", str(AUDIO_RATE), "-ac", "2",
               "-c:a", "pcm_s16le", str(out)]
    elif seg.get("use_source_audio") and seg.get("video"):
        start = max(0, int(seg.get("video_in_ms") or 0)) / 1000.0
        cmd = [FFMPEG, "-hide_banner", "-y", "-ss", f"{start:.3f}", "-i", seg["video"],
               "-vn", "-af", audio_filter, "-t", f"{seconds:.3f}",
               "-ar", str(AUDIO_RATE), "-ac", "2", "-c:a", "pcm_s16le", str(out)]
    else:
        cmd = [FFMPEG, "-hide_banner", "-y", "-f", "lavfi",
               "-i", f"anullsrc=r={AUDIO_RATE}:cl=stereo", "-t", f"{seconds:.3f}",
               "-c:a", "pcm_s16le", str(out)]
    _run(cmd, cwd=work, log=log)
    info = probe(out)
    if abs(info["duration_ms"] - seg["duration_ms"]) > 200:
        raise RuntimeError(f"{seg['id']}: audio duration {info['duration_ms']} ms "
                           f"!= declared {seg['duration_ms']} ms")
    return {"id": seg["id"], "duration_ms": info["duration_ms"], "file": str(out)}


def _concat_list(files: list[Path], path: Path) -> None:
    lines = []
    for item in files:
        escaped = str(item.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def concat_video(files: list[Path], out: Path, work: Path, *, encoder: str,
                 log: Path) -> None:
    listing = work / "video-concat.txt"
    _concat_list(files, listing)
    cmd = [FFMPEG, "-hide_banner", "-y", "-f", "concat", "-safe", "0",
           "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)]
    try:
        _run(cmd, cwd=work, log=log)
    except RuntimeError:
        cmd = [FFMPEG, "-hide_banner", "-y", "-f", "concat", "-safe", "0",
               "-i", str(listing), *_encoder_args(encoder), "-an", "-r", "30",
               "-movflags", "+faststart", str(out)]
        _run(cmd, cwd=work, log=log)


def concat_audio(files: list[Path], out: Path, work: Path, *, log: Path) -> None:
    listing = work / "audio-concat.txt"
    _concat_list(files, listing)
    cmd = [FFMPEG, "-hide_banner", "-y", "-f", "concat", "-safe", "0",
           "-i", str(listing), "-c", "copy", str(out)]
    try:
        _run(cmd, cwd=work, log=log)
    except RuntimeError:
        cmd = [FFMPEG, "-hide_banner", "-y", "-f", "concat", "-safe", "0",
               "-i", str(listing), "-c:a", "pcm_s16le", "-ar", str(AUDIO_RATE),
               "-ac", "2", str(out)]
        _run(cmd, cwd=work, log=log)


def mux_final(video: Path, audio: Path, ass: Path | None, out: Path, work: Path, *,
              width: int, height: int, fps: int, encoder: str, log: Path) -> None:
    cmd = [FFMPEG, "-hide_banner", "-y", "-i", str(video), "-i", str(audio)]
    if ass is not None:
        cmd += ["-vf", f"{_scrim_filter()},ass={ass.name}"]
    cmd += ["-af", "loudnorm=I=-16:TP=-1:LRA=11",
            "-map", "0:v:0", "-map", "1:a:0", *_encoder_args(encoder),
            "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", str(AUDIO_RATE), "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(out)]
    _run(cmd, cwd=work, log=log)


def verify_output(path: Path, timeline: dict[str, Any]) -> dict[str, Any]:
    info = probe(path)
    video = info.get("video") or {}
    audio = info.get("audio") or {}
    expected = int(timeline["total_ms"])
    checks = {
        "exists": path.is_file(),
        "nonempty": info["size"] > 0,
        "duration_ms": info["duration_ms"],
        "duration_ok": abs(info["duration_ms"] - expected) <= max(700, int(expected * 0.004)),
        "video_codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "resolution_ok": (video.get("width"), video.get("height")) ==
                         (timeline["width"], timeline["height"]),
        "fps": video.get("r_frame_rate"),
        "audio_codec": audio.get("codec_name"),
        "sample_rate": audio.get("sample_rate"),
        "has_audio": bool(audio),
    }
    checks["ok"] = all(value for key, value in checks.items()
                       if key in ("exists", "nonempty", "duration_ok", "resolution_ok", "has_audio"))
    return checks


def render_timeline(timeline: dict[str, Any], out_path: str | Path, *,
                    work_dir: str | Path | None = None, encoder: str = "auto",
                    burn_subs: bool = True) -> dict[str, Any]:
    total_start = time.monotonic()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = Path(work_dir) if work_dir else out_path.parent / "work" / f"render-{time.strftime('%Y%m%d-%H%M%S')}"
    work.mkdir(parents=True, exist_ok=True)
    log = work / "render.log"
    write_json(work / "timeline.json", timeline)

    cues = [Cue(**cue) for cue in timeline.get("cues", [])]
    ass_path = work / "subs.ass"
    if burn_subs and cues:
        subs.write_ass(cues, ass_path, width=timeline["width"], height=timeline["height"])

    encoders = ["qsv", "libx264"] if encoder == "auto" else [encoder]
    last_error: Exception | None = None
    for chosen in encoders:
        try:
            segment_reports = []
            visual_files: list[Path] = []
            audio_files: list[Path] = []
            for idx, seg in enumerate(timeline["segments"], start=1):
                visual = work / f"v-{idx:02d}-{seg['id']}.mp4"
                audio = work / f"a-{idx:02d}-{seg['id']}.wav"
                segment_reports.append(render_visual_segment(
                    seg, visual, work, width=timeline["width"], height=timeline["height"],
                    fps=timeline["fps"], encoder=chosen, log=log))
                render_audio_segment(seg, audio, work, log=log)
                visual_files.append(visual)
                audio_files.append(audio)
            video = work / "video.mp4"
            audio = work / "audio.wav"
            concat_video(visual_files, video, work, encoder=chosen, log=log)
            concat_audio(audio_files, audio, work, log=log)
            mux_final(video, audio, ass_path if (burn_subs and cues) else None,
                      out_path, work, width=timeline["width"], height=timeline["height"],
                      fps=timeline["fps"], encoder=chosen, log=log)
            checks = verify_output(out_path, timeline)
            report = {
                "ok": checks["ok"],
                "encoder": chosen,
                "output": str(out_path),
                "work_dir": str(work),
                "elapsed_s": round(time.monotonic() - total_start, 1),
                "segments": segment_reports,
                "checks": checks,
                "ass": str(ass_path) if ass_path.is_file() else None,
            }
            write_json(work / "render-report.json", report)
            if not checks["ok"]:
                raise RuntimeError(f"output verification failed: {checks}")
            return report
        except Exception as exc:  # noqa: BLE001 - retry with the next encoder
            last_error = exc
            if chosen != encoders[-1]:
                with log.open("a", encoding="utf-8") as handle:
                    handle.write(f"\n[encoder {chosen} failed: {exc}; retrying]\n")
                continue
            break
    raise RuntimeError(f"render failed: {last_error}; see {log}")


def _system_font() -> str:
    """Arial path escaped for an ffmpeg filter, derived from the environment."""
    windir = (os.environ.get("WINDIR") or os.environ.get("SystemRoot") or "").strip()
    if not windir:
        return ""
    font = Path(windir) / "Fonts" / "arial.ttf"
    if not font.is_file():
        return ""
    return str(font).replace("\\", "/").replace(":", "\\:")


def make_demo_image(path: Path, text: str, color: str = "0x0b0e13", *,
                    width: int = 1920, height: int = 1080) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = text.replace(":", "\\:").replace("'", "")
    if color.startswith("#"):
        color = "0x" + color[1:]
    font = _system_font()
    font_arg = f"fontfile='{font}':" if font else ""
    cmd = [FFMPEG, "-hide_banner", "-y", "-f", "lavfi",
           "-i", f"color=c={color}:s={width}x{height}:d=1", "-frames:v", "1",
           "-update", "1",
           "-vf", f"drawtext={font_arg}text='{safe}':fontcolor=white:fontsize=72:"
                  f"x=(w-text_w)/2:y=(h-text_h)/2",
           str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
