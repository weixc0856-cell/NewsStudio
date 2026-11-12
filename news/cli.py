"""Command line entry point: ``python -m news ...``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import capture, illustrate, or_export, render, tts
from .paths import episode_dir, resolve_out
from .plan import check_plan, draft_plan, load_plan, plan_stats
from .schemas import (
    SCHEMA_VERSION,
    load_json,
    parse_plan,
    parse_story_pack,
    write_json,
)
from .storypack import load_story_pack, summary as pack_summary
from .timeline import build_timeline, save_timeline, timeline_stats


def _print(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _load_pack_for(plan, plan_path: Path):
    raw = plan.story_pack
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = plan_path.parent / path
    return load_story_pack(path) if path.is_file() else None


def cmd_or_events(args: argparse.Namespace) -> int:
    events = or_export.list_events(args.db, min_sources=args.min_sources, limit=args.limit)
    if args.json:
        _print(events)
    else:
        for item in events:
            print(f"{item['event_id']}  src={item['sources']} fam={item['source_families']} "
                  f"ev={item['evidences']}  {item['title_norm'][:90]}")
    return 0


def cmd_or_export(args: argparse.Namespace) -> int:
    out = resolve_out(args.out)
    pack = or_export.export_to_file(
        args.db, args.event, out=out, title=args.title,
        rights_status=args.rights, sources_csv=args.sources_csv,
    )
    print(json.dumps(pack_summary(pack), ensure_ascii=False, indent=2))
    print(f"wrote {out}")
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    pack_path = Path(args.pack).expanduser().resolve()
    pack = load_story_pack(pack_path)
    plan = draft_plan(pack, args.episode)
    out = resolve_out(args.out) if args.out else episode_dir(args.episode) / "plan.json"
    try:
        plan.story_pack = pack_path.relative_to(out.parent.resolve()).as_posix()
    except ValueError:
        plan.story_pack = str(pack_path)
    write_json(out, plan.to_dict())
    errors, warnings = check_plan(plan, pack, base_dir=out.parent)
    _print({"out": str(out), "stats": plan_stats(plan), "errors": errors, "warnings": warnings})
    return 0 if not errors else 2


def cmd_validate(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_plan(plan_path)
    pack = _load_pack_for(plan, plan_path)
    errors, warnings = check_plan(plan, pack, base_dir=plan_path.parent,
                                  strict_files=args.strict_files)
    _print({"plan": str(plan_path), "stats": plan_stats(plan),
            "errors": errors, "warnings": warnings})
    return 0 if not errors else 2


def cmd_timeline(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_plan(plan_path)
    timeline, warnings = build_timeline(plan, base_dir=plan_path.parent,
                                        extend_for_narration=not args.strict_duration)
    out = resolve_out(args.out) if args.out else plan_path.with_name("timeline.json")
    save_timeline(timeline, out)
    _print({"out": str(out), "stats": timeline_stats(timeline), "warnings": warnings})
    return 0


def cmd_narrate(args: argparse.Namespace) -> int:
    result = tts.narrate_plan(str(Path(args.plan).expanduser().resolve()), force=args.force, speed=args.speed,
                              prompt_wav=args.prompt_wav, prompt_text=args.prompt_text,
                              base_url=args.base_url)
    _print({"episode_id": result["episode_id"],
            "segments": len(result["segments"]),
            "cached": sum(1 for s in result["segments"] if s.get("cached")),
            "plan": str(Path(args.plan))})
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    out = resolve_out(args.out)
    info = capture.screenshot_url(args.url, out, width=args.width, height=args.height,
                                  wait_ms=args.wait_ms, browser=args.browser)
    _print({**info, "out": str(out)})
    return 0


def cmd_capture_pack(args: argparse.Namespace) -> int:
    if not args.out_dir and not args.episode:
        raise SystemExit("capture-pack needs --out-dir or --episode")
    pack = load_story_pack(args.pack)
    out_dir = resolve_out(args.out_dir) if args.out_dir else episode_dir(args.episode) / "assets"
    results = capture.capture_coverage(pack, out_dir, limit=args.limit,
                                       width=args.width, height=args.height,
                                       wait_ms=args.wait_ms, browser=args.browser)
    _print(results)
    return 0

def cmd_card(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_plan(plan_path)
    segment = next((s for s in plan.segments if s.id == args.segment), None)
    if segment is None:
        raise SystemExit(f"segment not found: {args.segment}")
    out = resolve_out(args.out)
    info = capture.render_segment_card(
        segment.to_dict(), out, width=plan.width, height=plan.height,
        index=segment.id, work_dir=plan_path.parent / "work",
        browser=args.browser,
    )
    _print({**info, "out": str(out)})
    return 0


def cmd_illustrate(args: argparse.Namespace) -> int:
    out = resolve_out(args.out)
    meta = illustrate.generate(
        prompt=args.prompt, out=out, width=args.width, height=args.height,
        seed=args.seed, steps=args.steps, cfg=args.cfg,
        workflow_path=args.workflow, base_url=args.base_url,
        timeout_s=args.timeout, dry_run=args.dry_run,
    )
    _print({**meta, "out": str(out)})
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    timeline_path = Path(args.timeline).expanduser().resolve()
    timeline = load_json(timeline_path)
    out = resolve_out(args.out)
    work = Path(args.work).expanduser() if args.work else timeline_path.parent / "work" / "render"
    report = render.render_timeline(timeline, out, work_dir=work, encoder=args.encoder,
                                    burn_subs=not args.no_subs)
    _print(report)
    print(f"wrote {out}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    _print(render.probe(args.file))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    if args.plan:
        plan = load_plan(args.plan)
        _print(plan_stats(plan))
    else:
        _print(timeline_stats(load_json(args.timeline)))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    out = resolve_out(args.out)
    work = out.parent / "work" / "demo"
    work.mkdir(parents=True, exist_ok=True)
    img1 = work / "demo-card.png"
    img2 = work / "demo-quote.png"
    render.make_demo_image(img1, "NEWS / SOURCE CARD", "#0b0e13")
    render.make_demo_image(img2, "THIS IS A DEMO QUOTE", "#151a21")
    plan = parse_plan({
        "schema_version": SCHEMA_VERSION,
        "episode_id": "demo",
        "title": "Renderer demo",
        "story_pack": "",
        "segments": [
            {"id": "S01", "type": "source_card", "duration_ms": 3000,
             "title": "Demo", "subtitle": "Renderer self-test",
             "narration_text_en": "This is a renderer self test.",
             "image": str(img1)},
            {"id": "S02", "type": "quote", "duration_ms": 3000,
             "text_en": "A deterministic timeline.",
             "attribution": "NEWS PIPELINE",
             "narration_text_en": "A deterministic timeline.",
             "image": str(img2)},
        ],
    })
    timeline, warnings = build_timeline(plan, base_dir=work)
    report = render.render_timeline(timeline.to_dict(), out, work_dir=work,
                                    encoder=args.encoder, burn_subs=True)
    _print({"warnings": warnings, **report})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="news", description="English-first news commentary pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("or-events", help="list recent Opportunity Radar events (read-only)")
    p.add_argument("--db", required=True)
    p.add_argument("--min-sources", type=int, default=1)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_or_events)

    p = sub.add_parser("or-export", help="export a story pack (read-only)")
    p.add_argument("--db", required=True)
    p.add_argument("--event", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.add_argument("--rights", default="unknown")
    p.add_argument("--sources-csv")
    p.set_defaults(func=cmd_or_export)

    p = sub.add_parser("draft", help="draft a plan from a story pack")
    p.add_argument("--pack", required=True)
    p.add_argument("--episode", required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("validate", help="validate a plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--strict-files", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("timeline", help="build timeline.json from plan + narration WAVs")
    p.add_argument("--plan", required=True)
    p.add_argument("--out")
    p.add_argument("--strict-duration", action="store_true")
    p.set_defaults(func=cmd_timeline)

    p = sub.add_parser("narrate", help="synthesize English narration with VoxCPM2")
    p.add_argument("--plan", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--prompt-wav")
    p.add_argument("--prompt-text")
    p.add_argument("--base-url", default=tts.DEFAULT_BASE_URL)
    p.set_defaults(func=cmd_narrate)

    p = sub.add_parser("capture", help="capture a public page viewport")
    p.add_argument("--url", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--wait-ms", type=int, default=6000)
    p.add_argument("--browser")
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("capture-pack", help="capture one screenshot per coverage item")
    p.add_argument("--pack", required=True)
    p.add_argument("--episode")
    p.add_argument("--out-dir")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--wait-ms", type=int, default=6000)
    p.add_argument("--browser")
    p.set_defaults(func=cmd_capture_pack)

    p = sub.add_parser("card", help="render a source/quote card for one segment")
    p.add_argument("--plan", required=True)
    p.add_argument("--segment", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--browser")
    p.set_defaults(func=cmd_card)

    p = sub.add_parser("illustrate", help="generate an illustration with ComfyUI/FLUX")
    p.add_argument("--prompt", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=576)
    p.add_argument("--seed", type=int)
    p.add_argument("--steps", type=int, default=16)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--workflow")
    p.add_argument("--base-url", default=illustrate.DEFAULT_BASE_URL)
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_illustrate)

    p = sub.add_parser("render", help="render timeline.json to MP4")
    p.add_argument("--timeline", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--work")
    p.add_argument("--encoder", choices=("auto", "qsv", "libx264"), default="auto")
    p.add_argument("--no-subs", action="store_true")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("probe", help="ffprobe a file")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("stats", help="plan or timeline statistics")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan")
    group.add_argument("--timeline")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("demo", help="render a synthetic 6-second self-test")
    p.add_argument("--out", required=True)
    p.add_argument("--encoder", choices=("auto", "qsv", "libx264"), default="libx264")
    p.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
