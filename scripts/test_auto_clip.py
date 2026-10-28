"""Deterministic-logic tests for scripts/auto_clip.py (stdlib unittest only).

Run:
    .venv/Scripts/python.exe scripts/test_auto_clip.py
    # or
    uv run python -m unittest scripts/test_auto_clip.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_clip as ac  # noqa: E402

REAL_SRT = ac.ROOT / "subtitles" / "c88l8daXiv4.zh.bilingual.srt"


class RealSubtitleTests(unittest.TestCase):
    @unittest.skipUnless(REAL_SRT.exists(), "episode 21 SRT not present")
    def test_parse_episode_21(self) -> None:
        cues, errors = ac.parse_bilingual_srt(REAL_SRT)
        self.assertEqual(errors, [])
        self.assertEqual(len(cues), 317)
        self.assertEqual((cues[0].id, cues[0].start, cues[0].end), (1, 10040, 12670))
        self.assertEqual((cues[-1].id, cues[-1].end), (317, 1491920))
        self.assertEqual((cues[51].id, cues[51].start), (52, 295609))
        self.assertTrue(cues[51].top.startswith("brought this up"))
        self.assertTrue(cues[51].bottom)

    @unittest.skipUnless(REAL_SRT.exists(), "episode 21 SRT not present")
    def test_windows_episode_21(self) -> None:
        cues, _ = ac.parse_bilingual_srt(REAL_SRT)
        windows = ac.build_windows(cues, 660_000, 210_000, 180_000)
        self.assertEqual([(w.start, w.end) for w in windows],
                         [(0, 660_000), (450_000, 1_110_000), (900_000, 1_491_920)])
        self.assertEqual((windows[0].cue_ids[0], windows[0].cue_ids[-1]), (1, 121))
        self.assertEqual((windows[1].cue_ids[0], windows[1].cue_ids[-1]), (78, 238))
        self.assertEqual((windows[2].cue_ids[0], windows[2].cue_ids[-1]), (190, 317))

    @unittest.skipUnless(REAL_SRT.exists(), "episode 21 SRT not present")
    def test_clamp_episode_21(self) -> None:
        cues, _ = ac.parse_bilingual_srt(REAL_SRT)
        rows = ac.clamp_cues(cues, 295_609, 366_135)
        self.assertEqual((rows[0][0], rows[0][1]), (0, 5_338))
        self.assertEqual(rows[-1][1], 366_135)
        self.assertTrue(all(0 <= start < end <= 366_135 for start, end, _, _ in rows))


class WindowTests(unittest.TestCase):
    def test_cue_membership_is_intersection(self) -> None:
        cues = [ac.Cue(1, 0, 100, "a", ""), ac.Cue(2, 100, 200, "b", ""),
                ac.Cue(3, 200, 300, "c", "")]
        windows = ac.build_windows(cues, 200, 50, 100)
        # cue 2 touches both windows; cue 1 only the first; cue 3 only the second
        self.assertEqual(windows[0].cue_ids, [1, 2])
        self.assertEqual(windows[1].cue_ids, [2, 3])

    def test_short_tail_is_dropped(self) -> None:
        cues = [ac.Cue(1, 0, 650_000, "a", ""), ac.Cue(2, 650_000, 650_100, "b", "")]
        windows = ac.build_windows(cues, 660_000, 210_000, 180_000)
        self.assertEqual(len(windows), 1)


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cues = {
            1: ac.Cue(1, 0, 10_000, "a", ""),
            2: ac.Cue(2, 290_000, 300_000, "b", ""),
            3: ac.Cue(3, 10_000, 110_000, "c", ""),
            4: ac.Cue(4, 140_000, 210_000, "d", ""),
        }
        self.windows = [{"index": 0, "cue_ids": [1, 2]}, {"index": 1, "cue_ids": [3, 4]}]
        self.cfg = dict(ac.DEFAULTS)
        self.cfg.update(prefer_min_ms=240_000, prefer_max_ms=360_000)

    def test_ownership_and_timestamp_match(self) -> None:
        bad = {"source_window": 0, "start_cue_id": 1, "end_cue_id": 3,
               "start_ms": 0, "end_ms": 210_000, "duration_ms": 210_000}
        kept, removed = ac.filter_candidates([bad], self.windows, self.cues, self.cfg)
        self.assertEqual(kept, [])
        self.assertEqual(removed[0]["stage"], "ownership")

    def test_duration_gate(self) -> None:
        short = {"source_window": 0, "start_cue_id": 1, "end_cue_id": 2,
                 "start_ms": 0, "end_ms": 300_000, "duration_ms": 120_000}
        kept, removed = ac.filter_candidates([short], self.windows, self.cues, self.cfg)
        self.assertEqual(kept, [])
        self.assertEqual(removed[0]["stage"], "duration")

    def test_overlap_dedupe_prefers_preferred_duration(self) -> None:
        long = {"source_window": 0, "start_cue_id": 1, "end_cue_id": 2,
                "start_ms": 0, "end_ms": 300_000, "duration_ms": 300_000}
        other = {"source_window": 1, "start_cue_id": 3, "end_cue_id": 4,
                 "start_ms": 10_000, "end_ms": 210_000, "duration_ms": 200_000}
        kept, removed = ac.filter_candidates([other, long], self.windows, self.cues, self.cfg)
        self.assertEqual(kept, [long])
        self.assertEqual(removed[0]["stage"], "duplicate")
        self.assertEqual(removed[0]["duplicate_of"]["start_cue_id"], 1)

    def test_boundary_hard_reject(self) -> None:
        self.cues[1] = ac.Cue(1, 0, 300_000, "Yeah so like...", "")
        self.cues[2] = ac.Cue(2, 300_000, 600_000, "and because of that,", "")
        cand = {"source_window": 0, "start_cue_id": 1, "end_cue_id": 2,
                "start_ms": 0, "end_ms": 600_000, "duration_ms": 600_000}
        kept, removed = ac.filter_candidates([cand], self.windows, self.cues, self.cfg)
        self.assertEqual(kept, [])
        self.assertEqual(removed[0]["stage"], "boundary")
        self.assertIn("hard_reject", removed[0]["candidate"]["boundary_notes"])

    def test_boundary_low_score_is_kept(self) -> None:
        self.cues[1] = ac.Cue(1, 0, 300_000, "Like, it's not just that.", "")
        self.cues[2] = ac.Cue(2, 300_000, 600_000, "We need more cores.", "")
        cand = {"source_window": 0, "start_cue_id": 1, "end_cue_id": 2,
                "start_ms": 0, "end_ms": 600_000, "duration_ms": 600_000}
        kept, removed = ac.filter_candidates([cand], self.windows, self.cues, self.cfg)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["boundary_score"], 0)
        self.assertNotIn("hard_reject", kept[0]["boundary_notes"])

    def test_overlap_ratio_boundary(self) -> None:
        a = {"start_ms": 0, "end_ms": 300_000, "duration_ms": 300_000}
        b = {"start_ms": 0, "end_ms": 120_000, "duration_ms": 120_000}
        self.assertAlmostEqual(ac.overlap_ratio(a, b), 1.0)
        c = {"start_ms": 300_000, "end_ms": 600_000, "duration_ms": 300_000}
        self.assertEqual(ac.overlap_ratio(a, c), 0.0)


class StatusTests(unittest.TestCase):
    ok = staticmethod(lambda: {"status": "OK"})
    bad = staticmethod(lambda: {"status": "FAILED"})
    accepted = [{"acceptance": {"passed": True}}]
    rejected = [{"acceptance": {"passed": False}}]
    candidate = {"source_window": 0, "start_cue_id": 1, "end_cue_id": 2,
                 "start_ms": 0, "end_ms": 300_000, "duration_ms": 300_000}

    def test_matrix(self) -> None:
        fs = ac.final_status
        ok, bad = self.ok, self.bad
        acc, rej, cand = self.accepted, self.rejected, [self.candidate]
        self.assertEqual(fs([ok()], cand, acc), "SUCCESS")
        self.assertEqual(fs([ok()], [], []), "NO_CANDIDATES")
        self.assertEqual(fs([bad()], [], []), "ANALYSIS_FAILED")
        self.assertEqual(fs([ok(), bad()], cand, acc), "PARTIAL")
        self.assertEqual(fs([ok(), bad()], [], []), "ANALYSIS_FAILED")
        self.assertEqual(fs([ok()], cand, rej), "FAILED")
        self.assertEqual(fs([ok(), bad()], cand, rej), "FAILED")


class PathTests(unittest.TestCase):
    def test_relative_path_inside_root(self) -> None:
        path = ac.ROOT / "clips" / "a b" / "clip.ass"
        self.assertEqual(ac.escape_filter_path(path), "clips/a b/clip.ass")

    def test_absolute_path_escaping(self) -> None:
        path = Path("D:/x y/a,b[1];c.ass")
        self.assertEqual(ac.escape_filter_path(path), "D\\:/x y/a\\,b\\[1\\]\\;c.ass")



class BoundaryTests(unittest.TestCase):
    @staticmethod
    def cue(cid: int, top: str, start: int = 0, end: int = 1_000) -> ac.Cue:
        return ac.Cue(cid, start, end, top, "")

    def test_good_boundary_scores_high(self) -> None:
        score, notes = ac.boundary_score(
            self.cue(1, "Why is CPU becoming the bottleneck?"),
            self.cue(2, "That's the fundamental constraint."))
        self.assertGreaterEqual(score, 4)
        self.assertIn("question_boundary", notes)
        self.assertIn("terminal_end", notes)

    def test_filler_start_is_penalised_but_not_rejected(self) -> None:
        _, notes = ac.boundary_score(
            self.cue(1, "Like, it's not just that."),
            self.cue(2, "We need more cores."))
        self.assertIn("filler_start", notes)
        self.assertNotIn("hard_reject", notes)

    def test_continuation_end_is_penalised(self) -> None:
        _, notes = ac.boundary_score(
            self.cue(1, "The real issue is power."),
            self.cue(2, "and that's why..."))
        self.assertIn("continuation_end", notes)
        self.assertNotIn("hard_reject", notes)

    def test_double_negative_is_hard_reject(self) -> None:
        score, notes = ac.boundary_score(
            self.cue(1, "Yeah so like..."),
            self.cue(2, "and because of that,"))
        self.assertLessEqual(score, -1)
        self.assertIn("hard_reject", notes)

    def test_previous_question_counts(self) -> None:
        _, notes = ac.boundary_score(
            self.cue(2, "Because the memory bandwidth is limited."),
            self.cue(3, "That's the bottleneck."),
            prev=self.cue(1, "Why is this happening?"))
        self.assertIn("question_boundary", notes)

    def test_rank_prefers_higher_boundary_score(self) -> None:
        cfg = dict(ac.DEFAULTS)
        good = {"duration_ms": 300_000, "boundary_score": 4,
                "start_ms": 0, "start_cue_id": 1}
        weak = {"duration_ms": 300_000, "boundary_score": 0,
                "start_ms": 0, "start_cue_id": 1}
        self.assertLess(ac.rank_key(good, cfg), ac.rank_key(weak, cfg))

    def test_defaults_allow_ten_minutes(self) -> None:
        self.assertEqual(ac.DEFAULTS["max_clip_ms"], 600_000)
        self.assertEqual(ac.DEFAULTS["prefer_max_ms"], 420_000)


class PromptTests(unittest.TestCase):
    def test_prompt_requires_complete_argument(self) -> None:
        cues = [ac.Cue(1, 0, 1_000, "hello.", "")]
        win = ac.Window(0, 0, 1_000, [1])
        prompt = ac.build_prompt(win, cues, dict(ac.DEFAULTS))
        for token in ("问题明确", "结论完整", "解释充分", "可追溯",
                      "10 分钟", "闭环", "summary", "硬性下限", "短片段"):
            self.assertIn(token, prompt)
        self.assertIn("start_cue_id", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
