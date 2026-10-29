"""Offline CLI for the McKinsey-style static intro poster.

The core logic (template values, duration policy, static FFmpeg command) lives
in ``generate_intro.py`` and is used by the production stage 3/4 path.  This
wrapper is only for previewing a poster without touching the pipeline.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dub_mix  # noqa: E402
import generate_intro as gi  # noqa: E402
import resource_manager as rm  # noqa: E402

ROOT = gi.ROOT
SCHEMA_VERSION = 1
DEFAULTS = gi.POSTER_DEFAULTS
POSTER_TEMPLATE = gi.INTRO_TEMPLATE

# Re-exported for the tests and for callers that used the old module.
poster_values = gi.poster_values
plan_poster_duration = gi.plan_poster_duration
classify = gi.classify_poster_length
build_poster_command = gi.build_poster_command
render_poster_html = gi.render_poster_html


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (ROOT / p)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Static McKinsey-style intro poster")
    ap.add_argument("--out-dir", default=".runtime/poster")
    ap.add_argument("--title-en", required=True)
    ap.add_argument("--title-zh", required=True)
    ap.add_argument("--speaker", default="")
    ap.add_argument("--event", default="")
    ap.add_argument("--organization", default="")
    ap.add_argument("--verification", default="")
    ap.add_argument("--summary-zh", default="")
    ap.add_argument("--insight-1", default="")
    ap.add_argument("--insight-2", default="")
    ap.add_argument("--insight-3", default="")
    ap.add_argument("--kicker", default="TECHNICAL HIGHLIGHTS")
    ap.add_argument("--index", default="")
    ap.add_argument("--series", default="")
    ap.add_argument("--accent", default="#ff5500")
    ap.add_argument("--browser", default=None)
    ap.add_argument("--voice-wav", default=None)
    ap.add_argument("--silent", action="store_true")
    ap.add_argument("--duration-ms", type=int, default=None)
    args = ap.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        values = gi.poster_values(
            title_en=args.title_en, title_zh=args.title_zh, speaker=args.speaker,
            event=args.event, organization=args.organization,
            verification=args.verification, summary_zh=args.summary_zh,
            insight_1=args.insight_1, insight_2=args.insight_2,
            insight_3=args.insight_3, kicker=args.kicker, index=args.index,
            series=args.series, accent=args.accent)
    except ValueError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    voice: Path | None = None
    voice_ms: int | None = None
    if args.voice_wav and not args.silent:
        voice = resolve(args.voice_wav)
        if not voice.exists():
            print(f"voice wav not found: {voice}", file=sys.stderr)
            return 2
        voice_ms = round(gi.sd.probe_duration(voice) * 1000)
    try:
        plan = gi.plan_poster_duration(silent=voice is None, voice_ms=voice_ms,
                                       requested_ms=args.duration_ms)
    except ValueError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    try:
        html_path, png_path = gi.render_poster_html(values, out_dir, args.browser)
    except Exception as exc:
        log(f"poster render failed: {exc}")
        return 1
    log(f"poster: {rel(png_path)} ({plan['duration_ms']} ms, {plan['mode']})")

    out_path = out_dir / "poster.mp4"
    try:
        rm.assert_quiet(context="poster render (QSV)")
    except rm.ResourceBusyError as exc:
        log(f"resource check failed: {exc}")
        return 3
    gain = 1.0
    if voice is not None:
        gain = dub_mix.resolve_gain(
            voice, {"dub_target_db": dub_mix.DEFAULTS["dub_target_db"]})
    cmd = gi.build_poster_command(png=png_path, out=out_path,
                                  duration_ms=int(plan["duration_ms"]),
                                  voice=voice, gain=gain)
    proc = gi.run_cmd(cmd, timeout=600)
    if proc.returncode != 0:
        log(f"ffmpeg failed: {proc.stderr.strip()[-600:]}")
        return 1

    record = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "SUCCESS",
        "template": rel(gi.TEMPLATE_DIR / POSTER_TEMPLATE),
        "html": rel(html_path),
        "png": rel(png_path),
        "path": rel(out_path),
        "mode": plan["mode"],
        "duration_ms": plan["duration_ms"],
        "fps": int(DEFAULTS["fps"]),
        "size": f"{DEFAULTS['width']}x{DEFAULTS['height']}",
        "voice": rel(voice) if voice is not None else None,
        "copy": values,
        "ffmpeg_command": cmd,
    }
    (out_dir / "poster.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"poster video: {rel(out_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
