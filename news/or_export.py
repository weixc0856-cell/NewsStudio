"""Read-only export of a story pack from the Opportunity Radar SQLite database.

This module never writes to the Opportunity Radar database.  It opens the file
with ``mode=ro`` and emits a compact JSON document that the news production
pipeline can consume without depending on OR's internal Python package.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .schemas import (
    SCHEMA_VERSION,
    Claim,
    CoverageItem,
    Evidence,
    Source,
    StoryPack,
    parse_story_pack,
    write_json,
)


def _connect_ro(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Opportunity Radar database not found: {path}")
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _rows(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return list(con.execute(sql, tuple(params)))


def _load_rights(csv_path: str | Path | None) -> dict[str, str]:
    if not csv_path:
        return {}
    path = Path(csv_path)
    if not path.is_file():
        return {}
    rights: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source_id = (row.get("source_id") or "").strip()
            status = (row.get("permission_status") or "").strip()
            if source_id and status:
                rights[source_id] = status
    return rights


def export_story_pack(
    db_path: str | Path,
    event_id: str,
    *,
    title: str | None = None,
    rights_status: str = "unknown",
    sources_csv: str | Path | None = None,
) -> StoryPack:
    rights = _load_rights(sources_csv)
    con = _connect_ro(db_path)
    try:
        event = con.execute(
            "select * from events where event_id = ?", (event_id,)
        ).fetchone()
        if event is None:
            raise KeyError(f"event not found: {event_id}")
        articles = _rows(con, """
            select a.*, ea.relation, ea.assignment, ea.confidence
            from event_articles ea
            join articles a on a.article_key = ea.article_key
            where ea.event_id = ?
            order by a.published asc, a.article_key asc
        """, (event_id,))
        if not articles:
            raise KeyError(f"event has no articles: {event_id}")
        evidence_rows = _rows(con, """
            select ev.*
            from evidences ev
            join articles a on a.article_key = ev.article_key
            join event_articles ea on ea.article_key = a.article_key
            where ea.event_id = ?
            order by ev.observed_at asc, ev.evidence_id asc
        """, (event_id,))
        claim_rows = _rows(con, """
            select c.*
            from claims c
            where c.event_id = ?
            order by c.fact_ordinal asc, c.claim_id asc
        """, (event_id,))
        links = _rows(con, """
            select ce.claim_id, ce.evidence_id, ce.support
            from claim_evidence ce
            join claims c on c.claim_id = ce.claim_id
            where c.event_id = ?
        """, (event_id,))

        sources: dict[str, Source] = {}
        coverage: list[CoverageItem] = []
        for row in articles:
            source_id = row["source_id"] or row["article_key"]
            if source_id not in sources:
                sources[source_id] = Source(
                    source_id=source_id,
                    publisher=row["source_name"] or source_id,
                    title=row["title"] or "",
                    url=row["url"] or "",
                    published_at=row["published"] or "",
                    rights_status=rights.get(source_id, rights_status),
                )
            coverage.append(CoverageItem(
                publisher=row["source_name"] or source_id,
                headline=row["title"] or "",
                url=row["url"] or "",
                published_at=row["published"] or "",
            ))

        evidence: list[Evidence] = []
        seen_quotes: set[tuple[str, str]] = set()
        for row in evidence_rows:
            key = (row["source_id"] or "", row["quote"] or "")
            if key in seen_quotes:
                continue
            seen_quotes.add(key)
            locator: dict[str, Any] = {}
            if row["locator_json"]:
                try:
                    parsed = json.loads(row["locator_json"])
                    if isinstance(parsed, dict):
                        locator = parsed
                except json.JSONDecodeError:
                    locator = {"raw": row["locator_json"]}
            evidence.append(Evidence(
                evidence_id=row["evidence_id"],
                source_id=row["source_id"] or "",
                quote=row["quote"] or "",
                locator=locator,
                verification_state="unverified",
                kind=row["evidence_kind"] or "quote",
                source_family=row["source_family"] or "",
                independence=row["independence"] or "",
            ))

        by_claim: dict[str, list[str]] = {}
        for link in links:
            by_claim.setdefault(link["claim_id"], []).append(link["evidence_id"])
        claims: list[Claim] = []
        for row in claim_rows:
            claims.append(Claim(
                claim_id=row["claim_id"],
                text=row["value_text"] or row["quote"] or "",
                quote=row["quote"] or "",
                verification_state=row["verification_state"] or "unverified",
                evidence_ids=by_claim.get(row["claim_id"], []),
                kind=row["kind"] or "fact",
            ))

        chosen_title = title or max((a["title"] or "" for a in articles), key=len)
        pack = StoryPack(
            schema_version=SCHEMA_VERSION,
            story_id=event_id,
            title=chosen_title,
            event_key=event["event_key"] or "",
            first_seen_at=event["first_seen_at"] or "",
            last_seen_at=event["last_seen_at"] or "",
            sources=list(sources.values()),
            evidence=evidence,
            claims=claims,
            coverage=coverage,
            metadata={
                "backend": "opportunity_radar",
                "database": str(Path(db_path).resolve()),
                "event_id": event_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "article_count": len(articles),
                "source_count": len(sources),
                "source_family_count": len({e.source_family or e.source_id for e in evidence}),
                "publisher_count": len({c.publisher for c in coverage if c.publisher}),
                "note": "Quotes are short excerpts for verification; media rights are not granted by this export.",
            },
        )
        # Validate before returning so callers never receive a malformed pack.
        parse_story_pack(pack.to_dict())
        return pack
    finally:
        con.close()


def list_events(db_path: str | Path, *, min_sources: int = 1, limit: int = 20) -> list[dict[str, Any]]:
    con = _connect_ro(db_path)
    try:
        rows = _rows(con, """
            select e.event_id, e.title_norm, e.first_seen_at, e.last_seen_at,
                   count(distinct a.article_key) as articles,
                   count(distinct a.source_id) as sources,
                   count(distinct ev.source_family) as source_families,
                   count(ev.evidence_id) as evidences
            from events e
            join event_articles ea on ea.event_id = e.event_id
            join articles a on a.article_key = ea.article_key
            left join evidences ev on ev.article_key = a.article_key
            where e.merged_into is null
            group by e.event_id
            having sources >= ?
            order by e.last_seen_at desc, evidences desc
            limit ?
        """, (min_sources, limit))
        return [dict(row) for row in rows]
    finally:
        con.close()


def export_to_file(*args: Any, out: str | Path, **kwargs: Any) -> StoryPack:
    pack = export_story_pack(*args, **kwargs)
    write_json(out, pack.to_dict())
    return pack
