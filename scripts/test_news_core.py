from __future__ import annotations

import csv
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from news import subs  # noqa: E402
from news.or_export import export_story_pack, list_events  # noqa: E402
from news.plan import draft_plan, plan_stats  # noqa: E402
from news.schemas import (  # noqa: E402
    Cue,
    SchemaError,
    estimate_narration_ms,
    parse_plan,
    parse_story_pack,
    validate_plan,
)
from news.timeline import build_timeline  # noqa: E402


def story_dict() -> dict:
    return {
        "schema_version": 1,
        "story_id": "evt-test",
        "title": "A test story",
        "event_key": "https://example.com/story",
        "first_seen_at": "2026-11-10T00:00:00+00:00",
        "last_seen_at": "2026-11-11T00:00:00+00:00",
        "sources": [
            {"source_id": "s1", "publisher": "Publisher One",
             "title": "Headline one", "url": "https://example.com/one",
             "published_at": "2026-11-10T00:00:00+00:00",
             "rights_status": "approved"},
            {"source_id": "s2", "publisher": "Publisher Two",
             "title": "Headline two", "url": "https://example.com/two",
             "published_at": "2026-11-11T00:00:00+00:00",
             "rights_status": "approved"},
        ],
        "evidence": [
            {"evidence_id": "e1", "source_id": "s1", "quote": "Quote one",
             "locator": {"field": "body", "start": 0, "length": 9},
             "verification_state": "unverified", "kind": "quote"},
            {"evidence_id": "e2", "source_id": "s2", "quote": "Quote two",
             "locator": {"field": "body", "start": 4, "length": 9}},
        ],
        "claims": [
            {"claim_id": "c1", "text": "A claim", "quote": "Quote one",
             "verification_state": "unverified", "evidence_ids": ["e1"]},
        ],
        "coverage": [
            {"publisher": "Publisher One", "headline": "Headline one",
             "url": "https://example.com/one", "published_at": "2026-11-10T00:00:00+00:00"},
            {"publisher": "Publisher Two", "headline": "Headline two",
             "url": "https://example.com/two", "published_at": "2026-11-11T00:00:00+00:00"},
        ],
        "metadata": {},
    }


class StoryPackTests(unittest.TestCase):
    def test_parse_ok(self) -> None:
        pack = parse_story_pack(story_dict())
        self.assertEqual(pack.story_id, "evt-test")
        self.assertEqual(len(pack.sources), 2)
        self.assertEqual(len(pack.evidence), 2)

    def test_unknown_evidence_source_fails(self) -> None:
        data = story_dict()
        data["evidence"][0]["source_id"] = "missing"
        with self.assertRaises(SchemaError):
            parse_story_pack(data)

    def test_empty_sources_fails(self) -> None:
        data = story_dict()
        data["sources"] = []
        with self.assertRaises(SchemaError):
            parse_story_pack(data)


class PlanTests(unittest.TestCase):
    def _plan(self) -> dict:
        return {
            "schema_version": 1,
            "episode_id": "2026-11-12-test",
            "title": "Test episode",
            "story_pack": "story-pack.json",
            "fps": 30,
            "width": 1920,
            "height": 1080,
            "status": "draft",
            "segments": [
                {"id": "S01", "type": "source_card", "duration_ms": 8000,
                 "title": "Test story", "subtitle": "Two publishers",
                 "narration_text_en": "This is a short opening line."},
                {"id": "S02", "type": "quote", "duration_ms": 70000,
                 "text_en": "Quote one", "attribution": "Publisher One",
                 "narration_text_en": "This is the analysis paragraph that fills the rest of the episode.",
                 "evidence_refs": ["e1"]},
            ],
        }

    def test_valid_plan(self) -> None:
        pack = parse_story_pack(story_dict())
        plan = parse_plan(self._plan())
        errors, warnings = validate_plan(plan, pack=pack)
        self.assertEqual(errors, [])
        self.assertIsInstance(warnings, list)
        self.assertEqual(plan_stats(plan)["segments"], 2)

    def test_cjk_narration_rejected(self) -> None:
        data = self._plan()
        data["segments"][0]["narration_text_en"] = "这是中文"
        plan = parse_plan(data)
        errors, _ = validate_plan(plan)
        self.assertTrue(any("CJK" in e for e in errors))

    def test_unknown_evidence_ref_rejected(self) -> None:
        pack = parse_story_pack(story_dict())
        data = self._plan()
        data["segments"][1]["evidence_refs"] = ["missing"]
        plan = parse_plan(data)
        errors, _ = validate_plan(plan, pack=pack)
        self.assertTrue(any("unknown evidence_refs" in e for e in errors))

    def test_short_narration_window_rejected(self) -> None:
        data = self._plan()
        data["segments"][1]["duration_ms"] = 3000
        plan = parse_plan(data)
        errors, _ = validate_plan(plan)
        self.assertTrue(any("narration needs" in e for e in errors))

    def test_estimate(self) -> None:
        self.assertEqual(estimate_narration_ms(""), 0)
        self.assertGreater(estimate_narration_ms("one two three four five six seven"), 2000)

    def test_draft_plan_is_valid(self) -> None:
        pack = parse_story_pack(story_dict())
        plan = draft_plan(pack, "2026-11-12-test")
        errors, _ = validate_plan(plan, pack=pack)
        self.assertEqual(errors, [])
        self.assertTrue(plan.metadata["draft"])


class TimelineTests(unittest.TestCase):
    def test_build_with_fake_durations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.wav").write_bytes(b"")
            (base / "b.wav").write_bytes(b"")
            plan = parse_plan({
                "schema_version": 1,
                "episode_id": "ep",
                "title": "T",
                "story_pack": "s.json",
                "segments": [
                    {"id": "S01", "type": "source_card", "duration_ms": 5000,
                     "title": "T", "narration_text_en": "One sentence here.",
                     "narration_wav": "a.wav"},
                    {"id": "S02", "type": "quote", "duration_ms": 5000,
                     "text_en": "Quote", "attribution": "P",
                     "narration_text_en": "Another sentence here. And a second one.",
                     "narration_wav": "b.wav"},
                ],
            })
            timeline, warnings = build_timeline(
                plan, base_dir=base,
                duration_fn=lambda p: 9000 if Path(p).name == "a.wav" else 3000,
            )
            self.assertEqual(timeline.total_ms, 9400 + 5000)
            self.assertEqual(timeline.segments[0].duration_ms, 9400)
            self.assertGreaterEqual(len(timeline.cues), 2)
            self.assertTrue(any("extended" in w for w in warnings))
            self.assertEqual(timeline.cues[0].start_ms, 120)


class SubtitleTests(unittest.TestCase):
    def test_fmt_ass(self) -> None:
        self.assertEqual(subs.fmt_ass(0), "0:00:00.00")
        self.assertEqual(subs.fmt_ass(3_661_230), "1:01:01.23")

    def test_ass_text_wraps(self) -> None:
        en, zh = subs.ass_text("word " * 80, "中文" * 30)
        self.assertIn("\\N", en)
        self.assertIn("\\N", zh)

    def test_write_ass_and_srt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ass = Path(tmp) / "x.ass"
            srt = Path(tmp) / "x.srt"
            cues = [Cue(0, 1000, "Hello", "你好"), Cue(1000, 2500, "World")]
            subs.write_ass(cues, ass)
            subs.write_srt(cues, srt)
            text = ass.read_text(encoding="utf-8")
            self.assertIn("Dialogue:", text)
            self.assertIn("SubEn", text)
            self.assertIn("SubZh", text)
            self.assertIn("00:00:00,000 --> 00:00:01,000", srt.read_text(encoding="utf-8"))


class OrExportTests(unittest.TestCase):
    def _db(self, path: Path) -> None:
        con = sqlite3.connect(path)
        con.executescript("""
        create table events(event_id text, event_key text, event_type text, title_norm text,
            first_seen_at text, last_seen_at text, status text, merged_into text,
            rules_version text, created_at text);
        create table event_articles(event_id text, article_key text, relation text,
            assignment text, confidence real, reason text, created_at text);
        create table articles(article_key text, article_id text, title text, url text,
            published text, source_name text, summary_hash text, created_at text,
            fetched_at text, content_source text, retrieval_status text, event_key text,
            source_id text);
        create table evidences(evidence_id text, article_key text, source_id text,
            evidence_kind text, quote text, locator_json text, source_family text,
            independence text, observed_at text, rules_version text, created_at text,
            lineage_basis text, syndication_group text);
        create table claims(claim_id text, article_key text, event_id text, fact_ordinal integer,
            subject text, predicate text, value_num real, value_text text, unit text,
            currency text, region text, period text, comparison text, denominator text,
            seasonality text, revision text, kind text, quote text, locator_json text,
            verification_state text, extractor text, rules_version text, created_at text,
            verified_at text, verification_basis text, unit_raw text, scale text,
            period_raw text, revision_raw text);
        create table claim_evidence(claim_id text, evidence_id text, support text,
            independence text, locator_json text, created_at text);
        insert into events values('evt-1','https://example.com/story','','a test story',
            '2026-11-10','2026-11-11','open',null,'r1','2026-11-11');
        insert into articles values('a1','id1','Headline one','https://example.com/one',
            '2026-11-10','Publisher One','h1','x','x','rss','ok','k','s1');
        insert into articles values('a2','id2','Headline two','https://example.com/two',
            '2026-11-11','Publisher Two','h2','x','x','rss','ok','k','s2');
        insert into event_articles values('evt-1','a1','member','assigned',1.0,'','x');
        insert into event_articles values('evt-1','a2','member','assigned',1.0,'','x');
        insert into evidences values('e1','a1','s1','quote','Quote one',
            '{"field":"body","start":0,"length":9}','family1','independent','x','r1','x',null,null);
        insert into evidences values('e2','a2','s2','quote','Quote two',
            '{"field":"body","start":0,"length":9}','family2','independent','x','r1','x',null,null);
        insert into claims values('c1','a1','evt-1',1,'Subject','assertion',null,'A claim',
            '','','','','','','','','fact','Quote one','{}','unverified','n5','r2','x',null,null,'','','','');
        insert into claim_evidence values('c1','e1','supports','independent','{}','x');
        """)
        con.commit()
        con.close()

    def test_export_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "or.sqlite3"
            self._db(db)
            csv_path = Path(tmp) / "sources.csv"
            csv_path.write_text(
                "source_id,permission_status\ns1,approved\ns2,approved\n", encoding="utf-8")
            pack = export_story_pack(db, "evt-1", sources_csv=csv_path)
            self.assertEqual(pack.story_id, "evt-1")
            self.assertEqual(len(pack.sources), 2)
            self.assertEqual(len(pack.evidence), 2)
            self.assertEqual(pack.claims[0].evidence_ids, ["e1"])
            self.assertEqual(pack.sources[0].rights_status, "approved")
            events = list_events(db, min_sources=2)
            self.assertEqual(events[0]["event_id"], "evt-1")
            self.assertEqual(events[0]["sources"], 2)

    def test_missing_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "or.sqlite3"
            self._db(db)
            with self.assertRaises(KeyError):
                export_story_pack(db, "missing")


if __name__ == "__main__":
    unittest.main()
