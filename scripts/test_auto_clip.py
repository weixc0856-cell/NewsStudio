"""Deterministic-logic tests for scripts/auto_clip.py (stdlib unittest only).

Run:
    .venv/Scripts/python.exe scripts/test_auto_clip.py
    # or
    uv run python -m unittest scripts/test_auto_clip.py -v
"""
from __future__ import annotations

import sys
import unittest
from unittest import mock
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
                      "10 分钟", "3 分钟", "闭环", "summary", "优先 4–7 分钟"):
            self.assertIn(token, prompt)
        self.assertIn("start_cue_id", prompt)



class ExtendTests(unittest.TestCase):
    def test_extend_prompt_mentions_seconds_and_range(self) -> None:
        cues = [ac.Cue(i, (i - 1) * 60_000, i * 60_000, "text.", "")
                for i in range(1, 6)]
        win = ac.Window(0, 0, 300_000, [1, 2, 3, 4, 5])
        record = {"start_cue_id": 1, "end_cue_id": 2, "duration_ms": 60_000}
        prompt = ac.build_extend_prompt(win, cues, record, dict(ac.DEFAULTS))
        self.assertIn("60.0 秒", prompt)
        self.assertIn("180–420 秒", prompt)
        self.assertIn('{"end_cue_id"', prompt)

    def test_call_extend_model_parses_and_validates(self) -> None:
        cues = [ac.Cue(i, (i - 1) * 1_000, i * 1_000, "x", "")
                for i in range(1, 6)]
        win = ac.Window(0, 0, 6_000, [1, 2, 3, 4, 5])
        cfg = {**ac.DEFAULTS, "model_timeout_s": 10}
        response = mock.Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"end_cue_id": 4}'}}]}
        with mock.patch.object(ac.requests, "post", return_value=response):
            end_id, attempts = ac.call_extend_model(
                "http://x", "m", "p", win, 2, cfg)
        self.assertEqual(end_id, 4)
        self.assertTrue(attempts[0]["ok"])

    def test_call_extend_model_rejects_out_of_window(self) -> None:
        cues = [ac.Cue(i, (i - 1) * 1_000, i * 1_000, "x", "")
                for i in range(1, 4)]
        win = ac.Window(0, 0, 3_000, [1, 2, 3])
        cfg = {**ac.DEFAULTS, "model_timeout_s": 10}
        response = mock.Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"end_cue_id": 99}'}}]}
        with mock.patch.object(ac.requests, "post", return_value=response):
            end_id, attempts = ac.call_extend_model(
                "http://x", "m", "p", win, 1, cfg)
        self.assertIsNone(end_id)
        self.assertFalse(attempts[0]["ok"])


class AnalyzeExtendTests(unittest.TestCase):
    def cues(self) -> list[ac.Cue]:
        return [
            ac.Cue(1, 0, 60_000, "Why is CPU the bottleneck?", ""),
            ac.Cue(2, 60_000, 120_000, "Because the supply is fixed.", ""),
            ac.Cue(3, 120_000, 240_000, "Demand keeps rising.", ""),
            ac.Cue(4, 240_000, 300_000, "That is the constraint.", ""),
        ]

    def test_short_candidate_is_extended_once(self) -> None:
        cfg = {**ac.DEFAULTS, "base_url": "http://x", "model": "fake",
               "max_clips": 1, "srt_path": ac.ROOT / "subtitles/x.srt"}
        short = {"start_cue_id": 1, "end_cue_id": 2,
                 "title": "CPU", "summary": "supply"}
        with mock.patch.object(ac, "call_model",
                               return_value=(short, [{"ok": True}])),              mock.patch.object(ac, "call_extend_model",
                               return_value=(3, [{"ok": True}])) as extend:
            analysis = ac.analyze(self.cues(), cfg, "vid", None)
        self.assertTrue(analysis["windows"][0]["extended"])
        self.assertEqual(analysis["candidates_raw"][0]["end_cue_id"], 3)
        self.assertGreaterEqual(analysis["candidates_raw"][0]["duration_ms"], 180_000)
        self.assertEqual(extend.call_count, 1)

    def test_hard_reject_candidate_is_not_extended(self) -> None:
        cues = [ac.Cue(1, 0, 60_000, "Yeah so like...", ""),
                ac.Cue(2, 60_000, 120_000, "and because of that,", "")]
        cfg = {**ac.DEFAULTS, "base_url": "http://x", "model": "fake",
               "srt_path": ac.ROOT / "subtitles/x.srt"}
        short = {"start_cue_id": 1, "end_cue_id": 2,
                 "title": "x", "summary": "y"}
        with mock.patch.object(ac, "call_model",
                               return_value=(short, [{"ok": True}])),              mock.patch.object(ac, "call_extend_model") as extend:
            ac.analyze(cues, cfg, "vid", None)
        extend.assert_not_called()



class SoftClampTests(unittest.TestCase):
    def cues(self) -> dict[int, ac.Cue]:
        return {
            1: ac.Cue(1, 0, 120_000, "Question?", ""),
            2: ac.Cue(2, 120_000, 300_000, "Answer.", ""),
            3: ac.Cue(3, 300_000, 450_000, "and more...", ""),
            4: ac.Cue(4, 450_000, 547_000, "Conclusion.", ""),
        }

    def test_clamps_to_nearest_terminal_under_prefer(self) -> None:
        end = ac.soft_clamp_end(1, 4, self.cues(), dict(ac.DEFAULTS))
        self.assertEqual(end, 2)

    def test_returns_none_without_terminal_in_range(self) -> None:
        cues = {1: ac.Cue(1, 0, 120_000, "Question?", ""),
                2: ac.Cue(2, 120_000, 300_000, "and more...", ""),
                3: ac.Cue(3, 300_000, 450_000, "still going...", "")}
        self.assertIsNone(ac.soft_clamp_end(1, 3, cues, dict(ac.DEFAULTS)))


class OverlapTests(unittest.TestCase):
    def test_overlap_ms(self) -> None:
        a = {"start_ms": 0, "end_ms": 366_000}
        b = {"start_ms": 290_000, "end_ms": 800_000}
        self.assertEqual(ac.overlap_ms(a, b), 76_000)
        self.assertEqual(ac.overlap_ms(a, {"start_ms": 400_000, "end_ms": 500_000}), 0)

    def test_rank_penalises_overlap(self) -> None:
        cfg = dict(ac.DEFAULTS)
        a = {"start_ms": 0, "end_ms": 366_000, "duration_ms": 366_000,
             "boundary_score": 4, "start_cue_id": 1}
        b = {"start_ms": 290_000, "end_ms": 820_000, "duration_ms": 530_000,
             "boundary_score": 4, "start_cue_id": 2}
        self.assertEqual(ac.rank_key(a, cfg)[0], 0)
        self.assertEqual(ac.rank_key(b, cfg, (a,))[0], 1)

    def test_selection_prefers_non_overlapping_candidate(self) -> None:
        cues = {
            1: ac.Cue(1, 289_375, 661_744, "First topic conclusion.", ""),
            2: ac.Cue(2, 585_240, 1_115_560, "Overlapping long answer.", ""),
            3: ac.Cue(3, 944_175, 1_160_060, "Independent topic conclusion.", ""),
        }
        windows = [{"index": 0, "cue_ids": [1]},
                   {"index": 1, "cue_ids": [2]},
                   {"index": 2, "cue_ids": [3]}]
        a = {"source_window": 0, "start_cue_id": 1, "end_cue_id": 1,
             "start_ms": 289_375, "end_ms": 661_744, "duration_ms": 372_369,
             "title": "a", "summary": "a"}
        b = {"source_window": 1, "start_cue_id": 2, "end_cue_id": 2,
             "start_ms": 585_240, "end_ms": 1_115_560, "duration_ms": 530_320,
             "title": "b", "summary": "b"}
        c = {"source_window": 2, "start_cue_id": 3, "end_cue_id": 3,
             "start_ms": 944_175, "end_ms": 1_160_060, "duration_ms": 215_885,
             "title": "c", "summary": "c"}
        kept, removed = ac.filter_candidates([a, b, c], windows, cues, dict(ac.DEFAULTS))
        self.assertEqual([cand["start_cue_id"] for cand in kept], [1, 3])
        # the long overlapping candidate loses to the independent topic, then
        # is removed because it overlaps that topic by more than 0.4
        self.assertEqual(removed[0]["stage"], "duplicate")
        self.assertEqual(removed[0]["duplicate_of"]["start_cue_id"], 3)


class AnalyzeSoftClampTests(unittest.TestCase):
    def test_overlong_extension_is_clamped_to_a_terminal_cue(self) -> None:
        cues = [ac.Cue(1, 0, 120_000, "Question?", ""),
                ac.Cue(2, 120_000, 300_000, "Answer.", ""),
                ac.Cue(3, 300_000, 547_000, "Conclusion.", "")]
        cfg = {**ac.DEFAULTS, "base_url": "http://x", "model": "fake",
               "max_clips": 1, "srt_path": ac.ROOT / "subtitles/x.srt"}
        short = {"start_cue_id": 1, "end_cue_id": 1, "title": "t", "summary": "s"}
        with mock.patch.object(ac, "call_model",
                               return_value=(short, [{"ok": True}])),              mock.patch.object(ac, "call_extend_model",
                               return_value=(3, [{"ok": True}])):
            analysis = ac.analyze(cues, cfg, "vid", None)
        record = analysis["candidates_raw"][0]
        self.assertEqual(record["end_cue_id"], 2)
        self.assertEqual(record["duration_ms"], 300_000)
        self.assertEqual(record["soft_clamped_from"]["end_cue_id"], 3)
        self.assertTrue(analysis["windows"][0]["soft_clamped"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
