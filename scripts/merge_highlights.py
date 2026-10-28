"""Merge accepted highlight clips into one hard-cut highlight reel.

This script is intentionally separate from the candidate/render pipeline in
auto_clip.py: it only consumes clips that already passed acceptance.

Because the individual clips already carry burned-in subtitles, merging their
MP4s and burning a merged subtitle file again would double-render the text.
Instead this script re-reads the same source intervals (hard cuts), rebases the
per-clip SRT cues onto the merged timeline, and burns that merged subtitle file
once during a single QSV encode.

Usage:
    uv run python scripts/merge_highlights.py \
        --result clips/c88l8daXiv4/result.json

    # explicit source / output
    uv run python scripts/merge_highlights.py --result clips/<id>/result.json \
        --source "downloads/<video>.mkv" --out clips/<id>/final/highlights-merged.mp4
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_clip as ac  # noqa: E402


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (ac.ROOT / p)


def rel(path: Path) -> str:
    return ac.rel(path)


def human_duration(ms: int) -> str:
    """Human label used in notes; rounds up so 282.431s reads as 4m43s."""
    total_s = math.ceil(ms / 1000)
    m, s = divmod(total_s, 60)
    return f"{m}m{s:02d}s"


def load_accepted(result_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = json.loads(result_path.read_text(encoding="utf-8"))
    if data.get("status") not in ("SUCCESS", "PARTIAL"):
        raise RuntimeError(f"result status is {data.get('status')}; nothing to merge")
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
    accepted.sort(key=lambda c: c["start_ms"])
    return data, accepted


def build_segments(clips: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, list[int]]:
    segments: list[dict[str, Any]] = []
    offset = 0
    for clip in clips:
        segments.append({
            "clip_index": clip["index"],
            "title": clip.get("title", ""),
            "start_ms": clip["start_ms"],
            "end_ms": clip["start_ms"] + clip["duration_ms"],
            "duration_ms": clip["duration_ms"],
            "offset_ms": offset,
        })
        offset += clip["duration_ms"]
    gaps: list[int] = []
    for prev, cur in zip(segments, segments[1:]):
        gap = cur["start_ms"] - prev["end_ms"]
        if gap < 0:
            raise RuntimeError(f"clips {prev['clip_index']} and {cur['clip_index']} overlap")
        gaps.append(gap)
    return segments, offset, gaps


def build_expressions(segments: list[dict[str, Any]]) -> tuple[str, str, float]:
    """Return (select/aselect expression, timestamp offset expression, input read seconds)."""
    base = segments[0]["start_ms"]
    rel = [((s["start_ms"] - base) / 1000.0,
            (s["start_ms"] - base + s["duration_ms"]) / 1000.0) for s in segments]
    select = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in rel)

    terms: list[tuple[float, float]] = []
    cumulative = 0.0
    for k in range(1, len(rel)):
        cumulative += rel[k][0] - rel[k - 1][1]
        terms.append((rel[k][0], cumulative))
    offset = "+".join(f"gte(T,{start:.3f})*{gap:.3f}" for start, gap in terms) or "0"
    return select, offset, rel[-1][1]


def merge_subtitle_rows(clips: list[dict[str, Any]]) -> tuple[list[tuple[int, int, str, str]],
                                                               list[dict[str, Any]], int]:
    """Rebase each clip's clamped SRT onto the merged timeline."""
    rows: list[tuple[int, int, str, str]] = []
    segments: list[dict[str, Any]] = []
    offset = 0
    for clip in clips:
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
    if any(rows[i][0] < rows[i - 1][0] for i in range(1, len(rows))):
        raise RuntimeError("merged subtitle rows are not chronological")
    if rows and max(r[1] for r in rows) > offset:
        raise RuntimeError("merged subtitles overflow the merged duration")
    return rows, segments, offset


def merge_acceptance(path: Path, total_ms: int, rows: list[tuple[int, int, str, str]],
                     tolerance_ms: int) -> dict[str, Any]:
    cfg = {
        "duration_tolerance_ms": tolerance_ms,
        "video_codec": "h264",
        "audio_codec": "aac",
    }
    clip = {"start_ms": 0, "end_ms": total_ms, "duration_ms": total_ms}
    return ac.verify_clip(path, clip, rows, cfg)


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge accepted highlight clips (hard cuts)")
    ap.add_argument("--result", required=True, help="path to clips/<id>/result.json")
    ap.add_argument("--source", default=None, help="source video (default: result.json source)")
    ap.add_argument("--out", default=None, help="default: <result dir>/final/highlights-merged.mp4")
    ap.add_argument("--work-dir", default=None, help="default: <result dir>/work")
    ap.add_argument("--qsv-quality", type=int, default=ac.DEFAULTS["qsv_quality"])
    ap.add_argument("--audio-bitrate", default=ac.DEFAULTS["audio_bitrate"])
    ap.add_argument("--margin-v", type=int, default=ac.DEFAULTS["margin_v"])
    ap.add_argument("--duration-tolerance-ms", type=int, default=ac.DEFAULTS["duration_tolerance_ms"])
    ap.add_argument("--cfr", choices=("auto", "on", "off"), default="auto")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result_path = resolve(args.result)
    if not result_path.exists():
        print(f"result not found: {result_path}", file=sys.stderr)
        return 1
    out_dir = result_path.parent
    work_dir = Path(args.work_dir) if args.work_dir else out_dir / "work"
    if not work_dir.is_absolute():
        work_dir = resolve(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    ac.RUN.log_path = out_dir / "merge.log"
    ac.RUN.log(f"=== merge_highlights {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===")

    try:
        data, clips = load_accepted(result_path)
        segments, total_ms, gaps = build_segments(clips)
    except RuntimeError as exc:
        ac.RUN.log(f"cannot merge: {exc}")
        return 1

    source = Path(args.source) if args.source else data.get("source")
    if not source:
        ac.RUN.log("source video not provided and result.json has no source field")
        return 1
    source = resolve(source)
    if not source.exists():
        ac.RUN.log(f"source not found: {source}")
        return 1

    try:
        rows, subtitle_segments, subtitle_total = merge_subtitle_rows(clips)
        if subtitle_total != total_ms:
            raise RuntimeError(f"subtitle duration {subtitle_total} != clip total {total_ms}")
        select_expr, offset_expr, read_s = build_expressions(segments)
        source_info = ac.probe_source(source)
    except Exception as exc:
        ac.RUN.log(f"merge preparation failed: {exc}")
        return 1

    srt_path = work_dir / "highlights-merged.srt"
    ass_path = work_dir / "highlights-merged.ass"
    ac.write_srt([(s / 1000, e / 1000, top, bottom) for s, e, top, bottom in rows], srt_path)
    ac.write_ass([(s / 1000, e / 1000, top, bottom) for s, e, top, bottom in rows],
                 ass_path, margin_v=args.margin_v, top_only=False, font="Microsoft YaHei")

    out_path = Path(args.out) if args.out else out_dir / "final" / "highlights-merged.mp4"
    if not out_path.is_absolute():
        out_path = resolve(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_dir = out_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = work_dir / "highlights-merged.tmp.mp4"
    ffmpeg_log = work_dir / "highlights-merged.ffmpeg.log"

    base_ms = segments[0]["start_ms"]
    vf = (f"select='{select_expr}',"
          f"setpts='(PTS-STARTPTS)-({offset_expr})/TB',"
          f"ass={ac.escape_filter_path(ass_path)}")
    af = (f"aselect='{select_expr}',"
          f"asetpts='(PTS-STARTPTS)-({offset_expr})/TB'")
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-ss", f"{base_ms / 1000:.3f}", "-t", f"{read_s + 0.5:.3f}", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a:0", "-map_chapters", "-1",
        "-vf", vf, "-af", af,
        "-c:v", "h264_qsv", "-global_quality:v", str(args.qsv_quality), "-preset", "slow",
        "-c:a", "aac", "-b:a", args.audio_bitrate,
        "-sn", "-dn", "-movflags", "+faststart", "-avoid_negative_ts", "make_zero",
    ]
    if args.cfr == "on" or (args.cfr == "auto" and source_info["vfr"]):
        cmd += ["-fps_mode", "cfr", "-r", source_info["fps"]]
    cmd.append(str(tmp_path))

    ac.RUN.log(f"merging {len(segments)} segments, expected {total_ms} ms "
               f"(skipped {sum(gaps)} ms)")
    proc = ac.run_cmd(cmd, timeout=7200, log_path=ffmpeg_log)
    if proc.returncode != 0:
        ac.RUN.log(f"ffmpeg failed: {proc.stderr.strip()[-800:]}")
        merge = {
            "status": "FAILED",
            "error": f"ffmpeg exit {proc.returncode}",
            "expected_duration_ms": total_ms,
            "segments": segments,
            "gaps_ms": gaps,
            "skipped_ms": sum(gaps),
            "skipped_human": human_duration(sum(gaps)) if gaps else "0m00s",
            "acceptance": {"passed": False, "checks": []},
        }
        data["merge"] = merge
        ac.write_json(result_path, data)
        return 1

    acceptance = merge_acceptance(tmp_path, total_ms, rows, args.duration_tolerance_ms)
    if acceptance["passed"]:
        os.replace(tmp_path, out_path)
        target = out_path
    else:
        target = quarantine_dir / out_path.name
        os.replace(tmp_path, target)

    merge = {
        "status": "SUCCESS" if acceptance["passed"] else "FAILED",
        "output": rel(target) if acceptance["passed"] else None,
        "quarantined": None if acceptance["passed"] else rel(target),
        "expected_duration_ms": total_ms,
        "actual_duration_ms": acceptance.get("actual_duration_ms"),
        "segments": segments,
        "subtitle_segments": subtitle_segments,
        "gaps_ms": gaps,
        "skipped_ms": sum(gaps),
        "skipped_human": human_duration(sum(gaps)) if gaps else "0m00s",
        "note": (f"合集非连续剪辑，中间跳过约 {human_duration(sum(gaps))}"
                 f"（{sum(gaps)} ms）" if gaps else "片段连续，无跳过"),
        "subtitle_srt": rel(srt_path),
        "subtitle_ass": rel(ass_path),
        "acceptance": acceptance,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data["merge"] = merge
    ac.write_json(result_path, data)
    ac.RUN.log(f"merge status: {merge['status']} | {merge['expected_duration_ms']} ms "
               f"| skipped {merge['skipped_human']} | {merge['note']}")
    return 0 if acceptance["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
