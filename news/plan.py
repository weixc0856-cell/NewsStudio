"""Plan drafting and validation helpers."""
from __future__ import annotations

from pathlib import Path

from .schemas import (
    SCHEMA_VERSION,
    Plan,
    Segment,
    StoryPack,
    estimate_narration_ms,
    parse_plan,
    validate_plan,
)


def _first_evidence(pack: StoryPack, source_id: str) -> list[str]:
    for ev in pack.evidence:
        if ev.source_id == source_id:
            return [ev.evidence_id]
    return []


def _source_for_publisher(pack: StoryPack, publisher: str) -> str:
    for source in pack.sources:
        if source.publisher == publisher:
            return source.source_id
    return ""


def draft_plan(pack: StoryPack, episode_id: str) -> Plan:
    """Create a human-editable skeleton: card, coverage stills, commentary.

    All narration is a placeholder; the editor replaces it with the actual
    English commentary.  Images are expected under ``<episode>/assets/``.
    """
    publishers = ", ".join(sorted({s.publisher for s in pack.sources if s.publisher}))
    date = (pack.last_seen_at or pack.first_seen_at or "")[:10]
    segments = [
        Segment(
            id="S01",
            type="source_card",
            duration_ms=8_000,
            title=pack.title,
            subtitle=f"{date}  ·  {publishers}",
            narration_text_en="Today we look at a story covered by several outlets, and separate what is confirmed from what is still being argued.",
            sources=[s.publisher for s in pack.sources if s.publisher],
            note="Replace the opening narration with your own framing.",
        )
    ]
    evidence_ids = [e.evidence_id for e in pack.evidence]
    for idx, item in enumerate(pack.coverage[:3], start=1):
        source_id = _source_for_publisher(pack, item.publisher)
        segments.append(Segment(
            id=f"S{idx + 1:02d}",
            type="screenshot",
            duration_ms=12_000,
            image=f"assets/shot-{idx:02d}.png",
            narration_text_en=f"Here is how {item.publisher} frames the story in its own headline.",
            evidence_refs=_first_evidence(pack, source_id),
            sources=[item.publisher] if item.publisher else [],
            note=f"Capture the public page for {item.url}",
        ))
    quote = pack.claims[0].quote if pack.claims and pack.claims[0].quote else pack.title
    segments.append(Segment(
        id=f"S{len(segments) + 1:02d}",
        type="quote",
        duration_ms=60_000,
        text_en=quote,
        attribution=publishers,
        narration_text_en=(
            "This is the part most coverage agrees on. What it does not settle is the part that matters: "
            "who captures the value, what changes for customers, and which constraint becomes the bottleneck next."
        ),
        evidence_refs=evidence_ids[:3],
        note="Replace with your analysis and conclusion.",
    ))
    return Plan(
        schema_version=SCHEMA_VERSION,
        episode_id=episode_id,
        title=pack.title,
        story_pack=f"story-pack.json",
        segments=segments,
        status="draft",
        metadata={
            "draft": True,
            "target_length": "8-15 minutes",
            "instructions": [
                "Replace placeholder narration with English commentary.",
                "Capture screenshots into assets/ and point each segment at its file.",
                "Attach evidence_refs to every factual segment.",
                "Split long narration into one sentence per segment or add segments.",
            ],
        },
    )


def check_plan(plan: Plan, pack: StoryPack | None, base_dir: Path | None,
               strict_files: bool = False) -> tuple[list[str], list[str]]:
    return validate_plan(plan, pack=pack, base_dir=base_dir, strict_files=strict_files)


def plan_stats(plan: Plan) -> dict[str, object]:
    total = sum(max(0, s.duration_ms) for s in plan.segments)
    narration = sum(estimate_narration_ms(s.narration_text_en) for s in plan.segments)
    return {
        "episode_id": plan.episode_id,
        "segments": len(plan.segments),
        "total_ms": total,
        "total_seconds": round(total / 1000, 1),
        "estimated_narration_seconds": round(narration / 1000, 1),
        "factual_segments": sum(1 for s in plan.segments if s.type in {"screenshot", "chart", "clip"}),
        "segments_with_evidence": sum(1 for s in plan.segments if s.evidence_refs),
    }


def load_plan(path: str | Path) -> Plan:
    from .schemas import load_json

    return parse_plan(load_json(path))
