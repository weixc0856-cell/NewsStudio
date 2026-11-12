"""Build a deterministic timeline from a plan and the actual narration audio."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable

from .schemas import (
    SCHEMA_VERSION,
    Cue,
    Plan,
    Timeline,
    TimelineSegment,
    write_json,
)

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
LEAD_MS = 120
TAIL_MS = 160


def probe_duration_ms(path: str | Path) -> int:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"audio not found: {p}")
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(p),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return int(round(float(out.stdout.strip()) * 1000))


def _sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_RE.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _cues_for_segment(start: int, duration: int, text_en: str, text_zh: str,
                      narration_ms: int) -> list[Cue]:
    parts_en = _sentences(text_en)
    if not parts_en:
        return []
    usable = max(500, min(duration - LEAD_MS - TAIL_MS, narration_ms or duration - LEAD_MS - TAIL_MS))
    cue_start = start + LEAD_MS
    cue_end_limit = start + duration - TAIL_MS
    weights = [max(1, len(re.findall(r"[A-Za-z0-9']+", p))) for p in parts_en]
    total_weight = sum(weights)
    parts_zh = _sentences(text_zh) if text_zh else []
    cues: list[Cue] = []
    cursor = cue_start
    for idx, part in enumerate(parts_en):
        span = max(800, int(round(usable * weights[idx] / total_weight)))
        end = min(cue_end_limit, cursor + span)
        if end <= cursor:
            break
        zh = parts_zh[idx] if idx < len(parts_zh) else ""
        cues.append(Cue(cursor, end, part, zh))
        cursor = end
    return cues


def build_timeline(plan: Plan, base_dir: str | Path | None = None,
                   duration_fn: Callable[[str | Path], int] | None = None,
                   extend_for_narration: bool = True) -> tuple[Timeline, list[str]]:
    """Return (timeline, warnings).

    If a narration WAV is longer than the declared segment duration, the segment
    is extended to fit the audio (TTS duration is authoritative).  Pass
    ``extend_for_narration=False`` to keep declared durations.
    """
    base = Path(base_dir) if base_dir else None
    duration_fn = duration_fn or probe_duration_ms
    warnings: list[str] = []
    segments: list[TimelineSegment] = []
    cues: list[Cue] = []
    cursor = 0
    for seg in plan.segments:
        wav = seg.narration_wav
        wav_path: Path | None = None
        if wav:
            wav_path = Path(wav).expanduser()
            if not wav_path.is_absolute() and base is not None:
                wav_path = base / wav_path
        narration_ms = 0
        if wav_path is not None and wav_path.is_file():
            narration_ms = duration_fn(wav_path)
        elif wav:
            warnings.append(f"{seg.id}: narration wav not found, using declared duration: {wav}")
        duration = seg.duration_ms
        if extend_for_narration and narration_ms and narration_ms > duration - 250:
            duration = narration_ms + 400
            warnings.append(f"{seg.id}: extended {seg.duration_ms} -> {duration} ms for narration")
        start = cursor
        end = start + duration

        def _abs(raw: str) -> str:
            if not raw:
                return ""
            p = Path(raw).expanduser()
            if not p.is_absolute() and base is not None:
                p = base / p
            return str(p)

        segment = TimelineSegment(
            id=seg.id,
            type=seg.type,
            start_ms=start,
            end_ms=end,
            duration_ms=duration,
            motion=seg.motion,
            image=_abs(seg.image),
            video=_abs(seg.video),
            video_in_ms=seg.video_in_ms,
            use_source_audio=seg.use_source_audio,
            narration_wav=str(wav_path) if wav_path and wav_path.is_file() else "",
            title=seg.title,
            subtitle=seg.subtitle,
            text_en=seg.text_en,
            attribution=seg.attribution,
            sources=list(seg.sources),
            evidence_refs=list(seg.evidence_refs),
        )
        segments.append(segment)
        if seg.narration_text_en.strip():
            cues.extend(_cues_for_segment(start, duration, seg.narration_text_en,
                                          seg.narration_text_zh, narration_ms))
        elif seg.text_en.strip():
            cues.extend(_cues_for_segment(start, duration, seg.text_en, "", 0))
        cursor = end
    timeline = Timeline(
        schema_version=SCHEMA_VERSION,
        episode_id=plan.episode_id,
        title=plan.title,
        fps=plan.fps,
        width=plan.width,
        height=plan.height,
        total_ms=cursor,
        segments=segments,
        cues=cues,
        metadata={"story_pack": plan.story_pack, "plan_status": plan.status},
    )
    return timeline, warnings


def save_timeline(timeline: Timeline, path: str | Path) -> None:
    write_json(path, timeline.to_dict())


def timeline_stats(timeline: Timeline) -> dict[str, object]:
    return {
        "episode_id": timeline.episode_id,
        "total_seconds": round(timeline.total_ms / 1000, 1),
        "segments": len(timeline.segments),
        "cues": len(timeline.cues),
        "narrated_segments": sum(1 for s in timeline.segments if s.narration_wav),
    }
