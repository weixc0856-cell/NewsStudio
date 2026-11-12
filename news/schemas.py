"""Strict, dependency-free contracts for story packs, plans and timelines.

All times are integer milliseconds.  The model never supplies timing: timing is
declared in the plan and re-derived from the actual narration WAV durations in
``timeline.py``.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_FPS = 30
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
MIN_TOTAL_MS = 60 * 1000
MAX_TOTAL_MS = 30 * 60 * 1000
MIN_SEGMENT_MS = 2_000
MAX_SEGMENT_MS = 180_000

SEGMENT_TYPES = {
    "source_card",   # typographic card: publisher, headline, date, sources
    "screenshot",    # captured news page / official page
    "illustration",  # generated or licensed illustration (never evidence)
    "chart",         # data chart (own or public data)
    "clip",          # short video excerpt, optional source audio
    "quote",         # typographic quote card
}
FACTUAL_TYPES = {"screenshot", "chart", "clip"}
CJK_RE = re.compile(r"[㐀-鿿]")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")
WORDS_PER_SECOND = 140 / 60.0  # English narration target, ~140 wpm


class SchemaError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _s(data: dict[str, Any], key: str, where: str, errors: list[str], default: str = "") -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        errors.append(f"{where}.{key}: expected string")
        return default
    return value


def _i(data: dict[str, Any], key: str, where: str, errors: list[str], default: int = 0) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{where}.{key}: expected integer")
        return default
    return value


def _list(data: dict[str, Any], key: str, where: str, errors: list[str]) -> list[Any]:
    value = data.get(key, [])
    if not isinstance(value, list):
        errors.append(f"{where}.{key}: expected list")
        return []
    return value


# --------------------------------------------------------------------------
# story pack
# --------------------------------------------------------------------------
@dataclass
class Source:
    source_id: str
    publisher: str
    title: str
    url: str
    published_at: str = ""
    rights_status: str = "unknown"


@dataclass
class Evidence:
    evidence_id: str
    source_id: str
    quote: str
    locator: dict[str, Any] = field(default_factory=dict)
    verification_state: str = "unverified"
    kind: str = "quote"
    source_family: str = ""
    independence: str = ""


@dataclass
class Claim:
    claim_id: str
    text: str
    quote: str = ""
    verification_state: str = "unverified"
    evidence_ids: list[str] = field(default_factory=list)
    kind: str = "fact"


@dataclass
class CoverageItem:
    publisher: str
    headline: str
    url: str
    published_at: str = ""


@dataclass
class StoryPack:
    schema_version: int
    story_id: str
    title: str
    event_key: str = ""
    first_seen_at: str = ""
    last_seen_at: str = ""
    sources: list[Source] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    coverage: list[CoverageItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_story_pack(data: dict[str, Any]) -> StoryPack:
    errors: list[str] = []
    if not isinstance(data, dict):
        raise SchemaError(["story pack: expected object"])
    version = _i(data, "schema_version", "story_pack", errors, SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        errors.append(f"story_pack.schema_version: unsupported {version}")
    sources: list[Source] = []
    for idx, item in enumerate(_list(data, "sources", "story_pack", errors)):
        where = f"sources[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        sources.append(Source(
            source_id=_s(item, "source_id", where, errors),
            publisher=_s(item, "publisher", where, errors),
            title=_s(item, "title", where, errors),
            url=_s(item, "url", where, errors),
            published_at=_s(item, "published_at", where, errors),
            rights_status=_s(item, "rights_status", where, errors, "unknown"),
        ))
    evidence: list[Evidence] = []
    for idx, item in enumerate(_list(data, "evidence", "story_pack", errors)):
        where = f"evidence[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        locator = item.get("locator", {})
        if not isinstance(locator, dict):
            errors.append(f"{where}.locator: expected object")
            locator = {}
        evidence.append(Evidence(
            evidence_id=_s(item, "evidence_id", where, errors),
            source_id=_s(item, "source_id", where, errors),
            quote=_s(item, "quote", where, errors),
            locator=locator,
            verification_state=_s(item, "verification_state", where, errors, "unverified"),
            kind=_s(item, "kind", where, errors, "quote"),
            source_family=_s(item, "source_family", where, errors),
            independence=_s(item, "independence", where, errors),
        ))
    claims: list[Claim] = []
    for idx, item in enumerate(_list(data, "claims", "story_pack", errors)):
        where = f"claims[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        ids = item.get("evidence_ids", [])
        if not isinstance(ids, list) or any(not isinstance(v, str) for v in ids):
            errors.append(f"{where}.evidence_ids: expected list[str]")
            ids = []
        claims.append(Claim(
            claim_id=_s(item, "claim_id", where, errors),
            text=_s(item, "text", where, errors),
            quote=_s(item, "quote", where, errors),
            verification_state=_s(item, "verification_state", where, errors, "unverified"),
            evidence_ids=list(ids),
            kind=_s(item, "kind", where, errors, "fact"),
        ))
    coverage: list[CoverageItem] = []
    for idx, item in enumerate(_list(data, "coverage", "story_pack", errors)):
        where = f"coverage[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        coverage.append(CoverageItem(
            publisher=_s(item, "publisher", where, errors),
            headline=_s(item, "headline", where, errors),
            url=_s(item, "url", where, errors),
            published_at=_s(item, "published_at", where, errors),
        ))
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("story_pack.metadata: expected object")
        metadata = {}
    pack = StoryPack(
        version,
        _s(data, "story_id", "story_pack", errors),
        _s(data, "title", "story_pack", errors),
        _s(data, "event_key", "story_pack", errors),
        _s(data, "first_seen_at", "story_pack", errors),
        _s(data, "last_seen_at", "story_pack", errors),
        sources, evidence, claims, coverage, metadata,
    )
    errors.extend(validate_story_pack(pack))
    if errors:
        raise SchemaError(errors)
    return pack


def validate_story_pack(pack: StoryPack) -> list[str]:
    errors: list[str] = []
    if not pack.story_id:
        errors.append("story_id is empty")
    if not pack.title:
        errors.append("title is empty")
    if not pack.sources:
        errors.append("sources is empty")
    if not pack.coverage:
        errors.append("coverage is empty")
    source_ids = {s.source_id for s in pack.sources}
    for source in pack.sources:
        if not source.source_id:
            errors.append("source.source_id is empty")
        if not source.url:
            errors.append(f"source {source.source_id}: url is empty")
    for ev in pack.evidence:
        if ev.source_id not in source_ids:
            errors.append(f"evidence {ev.evidence_id}: unknown source_id {ev.source_id}")
        if not ev.quote.strip():
            errors.append(f"evidence {ev.evidence_id}: empty quote")
    evidence_ids = {e.evidence_id for e in pack.evidence}
    for claim in pack.claims:
        for eid in claim.evidence_ids:
            if eid not in evidence_ids:
                errors.append(f"claim {claim.claim_id}: unknown evidence_id {eid}")
    return errors


# --------------------------------------------------------------------------
# plan
# --------------------------------------------------------------------------
@dataclass
class Segment:
    id: str
    type: str
    duration_ms: int
    narration_text_en: str = ""
    narration_text_zh: str = ""
    narration_wav: str = ""
    image: str = ""
    video: str = ""
    video_in_ms: int = 0
    use_source_audio: bool = False
    motion: str = "zoom-in"
    title: str = ""
    subtitle: str = ""
    text_en: str = ""
    attribution: str = ""
    sources: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Plan:
    schema_version: int
    episode_id: str
    title: str
    story_pack: str
    segments: list[Segment]
    fps: int = DEFAULT_FPS
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_plan(data: dict[str, Any]) -> Plan:
    errors: list[str] = []
    if not isinstance(data, dict):
        raise SchemaError(["plan: expected object"])
    version = _i(data, "schema_version", "plan", errors, SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        errors.append(f"plan.schema_version: unsupported {version}")
    segments: list[Segment] = []
    for idx, item in enumerate(_list(data, "segments", "plan", errors)):
        where = f"segments[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        refs = item.get("evidence_refs", [])
        srcs = item.get("sources", [])
        if not isinstance(refs, list) or any(not isinstance(v, str) for v in refs):
            errors.append(f"{where}.evidence_refs: expected list[str]")
            refs = []
        if not isinstance(srcs, list) or any(not isinstance(v, str) for v in srcs):
            errors.append(f"{where}.sources: expected list[str]")
            srcs = []
        segments.append(Segment(
            id=_s(item, "id", where, errors),
            type=_s(item, "type", where, errors),
            duration_ms=_i(item, "duration_ms", where, errors),
            narration_text_en=_s(item, "narration_text_en", where, errors),
            narration_text_zh=_s(item, "narration_text_zh", where, errors),
            narration_wav=_s(item, "narration_wav", where, errors),
            image=_s(item, "image", where, errors),
            video=_s(item, "video", where, errors),
            video_in_ms=_i(item, "video_in_ms", where, errors),
            use_source_audio=bool(item.get("use_source_audio", False)),
            motion=_s(item, "motion", where, errors, "zoom-in"),
            title=_s(item, "title", where, errors),
            subtitle=_s(item, "subtitle", where, errors),
            text_en=_s(item, "text_en", where, errors),
            attribution=_s(item, "attribution", where, errors),
            sources=srcs,
            evidence_refs=refs,
            note=_s(item, "note", where, errors),
        ))
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("plan.metadata: expected object")
        metadata = {}
    plan = Plan(
        version,
        _s(data, "episode_id", "plan", errors),
        _s(data, "title", "plan", errors),
        _s(data, "story_pack", "plan", errors),
        segments,
        _i(data, "fps", "plan", errors, DEFAULT_FPS),
        _i(data, "width", "plan", errors, DEFAULT_WIDTH),
        _i(data, "height", "plan", errors, DEFAULT_HEIGHT),
        _s(data, "status", "plan", errors, "draft"),
        metadata,
    )
    if errors:
        raise SchemaError(errors)
    return plan


def estimate_narration_ms(text: str) -> int:
    words = len(WORD_RE.findall(text or ""))
    return int(round(words / WORDS_PER_SECOND * 1000))


def _resolve(base: Path | None, raw: str) -> Path:
    p = Path(raw).expanduser()
    if base is not None and not p.is_absolute():
        p = base / p
    return p


def validate_plan(plan: Plan, pack: StoryPack | None = None, base_dir: Path | None = None,
                  strict_files: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not plan.episode_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", plan.episode_id):
        errors.append("episode_id must match [A-Za-z0-9][A-Za-z0-9._-]*")
    if not plan.title.strip():
        errors.append("title is empty")
    if plan.fps not in (24, 25, 30, 50, 60):
        errors.append(f"fps {plan.fps} is not supported")
    if plan.fps != DEFAULT_FPS:
        warnings.append(f"renderer is validated at {DEFAULT_FPS} fps; got {plan.fps}")
    if plan.width <= 0 or plan.height <= 0 or plan.width % 2 or plan.height % 2:
        errors.append("width/height must be positive even integers")
    if not plan.segments:
        errors.append("segments is empty")
    ids: set[str] = set()
    total = 0
    evidence_ids = {e.evidence_id for e in pack.evidence} if pack else None
    for seg in plan.segments:
        where = f"segment {seg.id or '?'}"
        if not seg.id:
            errors.append("segment id is empty")
        elif seg.id in ids:
            errors.append(f"{where}: duplicate id")
        ids.add(seg.id)
        if seg.type not in SEGMENT_TYPES:
            errors.append(f"{where}: unknown type {seg.type!r}")
        if not (MIN_SEGMENT_MS <= seg.duration_ms <= MAX_SEGMENT_MS):
            errors.append(f"{where}: duration_ms {seg.duration_ms} outside "
                          f"{MIN_SEGMENT_MS}..{MAX_SEGMENT_MS}")
        total += max(0, seg.duration_ms)
        if seg.type in ("screenshot", "illustration", "chart") and not seg.image:
            errors.append(f"{where}: image is required for {seg.type}")
        if seg.type == "clip" and not seg.video:
            errors.append(f"{where}: video is required for clip")
        if seg.type == "source_card" and not (seg.title or seg.subtitle):
            errors.append(f"{where}: source_card needs title or subtitle")
        if seg.type == "quote" and not (seg.text_en or seg.attribution):
            errors.append(f"{where}: quote needs text_en or attribution")
        if seg.motion not in ("zoom-in", "zoom-out", "pan-left", "pan-right", "static"):
            errors.append(f"{where}: unknown motion {seg.motion!r}")
        if CJK_RE.search(seg.narration_text_en):
            errors.append(f"{where}: narration_text_en contains CJK characters")
        if seg.narration_text_en.strip():
            est = estimate_narration_ms(seg.narration_text_en)
            if seg.duration_ms < est * 0.85:
                errors.append(f"{where}: narration needs ~{est} ms, declared {seg.duration_ms} ms")
            elif seg.duration_ms > max(est * 3.0, est + 12_000):
                warnings.append(f"{where}: {seg.duration_ms} ms is much longer than "
                                f"narration (~{est} ms)")
        elif seg.type != "clip" or not seg.use_source_audio:
            errors.append(f"{where}: English narration text is required")
        if seg.evidence_refs and evidence_ids is not None:
            for eid in seg.evidence_refs:
                if eid not in evidence_ids:
                    errors.append(f"{where}: unknown evidence_refs {eid}")
        if seg.type in FACTUAL_TYPES and not seg.evidence_refs:
            warnings.append(f"{where}: factual segment has no evidence_refs")
        if strict_files:
            for attr in ("image", "video", "narration_wav"):
                raw = getattr(seg, attr)
                if raw and not _resolve(base_dir, raw).is_file():
                    errors.append(f"{where}: {attr} not found: {raw}")
    if not (MIN_TOTAL_MS <= total <= MAX_TOTAL_MS):
        errors.append(f"total duration {total} ms outside {MIN_TOTAL_MS}..{MAX_TOTAL_MS}")
    return errors, warnings


# --------------------------------------------------------------------------
# timeline
# --------------------------------------------------------------------------
@dataclass
class Cue:
    start_ms: int
    end_ms: int
    text_en: str
    text_zh: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineSegment:
    id: str
    type: str
    start_ms: int
    end_ms: int
    duration_ms: int
    motion: str
    image: str
    video: str
    video_in_ms: int
    use_source_audio: bool
    narration_wav: str
    title: str
    subtitle: str
    text_en: str
    attribution: str
    sources: list[str]
    evidence_refs: list[str]

    @property
    def seconds(self) -> float:
        return self.duration_ms / 1000.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["seconds"] = self.seconds
        return data


@dataclass
class Timeline:
    schema_version: int
    episode_id: str
    title: str
    fps: int
    width: int
    height: int
    total_ms: int
    segments: list[TimelineSegment]
    cues: list[Cue]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_id": self.episode_id,
            "title": self.title,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "total_ms": self.total_ms,
            "segments": [s.to_dict() for s in self.segments],
            "cues": [c.to_dict() for c in self.cues],
            "metadata": self.metadata,
        }
