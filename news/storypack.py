"""Story-pack loading and summarising."""
from __future__ import annotations

from pathlib import Path

from .schemas import StoryPack, load_json, parse_story_pack, write_json


def load_story_pack(path: str | Path) -> StoryPack:
    return parse_story_pack(load_json(path))


def save_story_pack(pack: StoryPack, path: str | Path) -> None:
    write_json(path, pack.to_dict())


def summary(pack: StoryPack) -> dict[str, object]:
    publishers = {s.publisher for s in pack.sources if s.publisher}
    families = {e.source_family or e.source_id for e in pack.evidence}
    return {
        "story_id": pack.story_id,
        "title": pack.title,
        "sources": len(pack.sources),
        "publishers": sorted(publishers),
        "publisher_count": len(publishers),
        "source_families": len(families),
        "coverage": len(pack.coverage),
        "evidence": len(pack.evidence),
        "claims": len(pack.claims),
        "verified_claims": sum(1 for c in pack.claims if c.verification_state == "verified"),
    }
