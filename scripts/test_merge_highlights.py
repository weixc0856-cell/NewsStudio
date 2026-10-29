"""Tests for merge_highlights.py (stdlib unittest only).

Run:
    .venv/Scripts/python.exe scripts/test_merge_highlights.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_clip as ac  # noqa: E402
import merge_highlights as mh  # noqa: E402

RESULT = ac.ROOT / "clips" / "c88l8daXiv4" / "result.json"


def fake_clips() -> list[dict]:
    return [
        {"index": 1, "start_ms": 289_375, "duration_ms": 372_369, "title": "a"},
        {"index": 2, "start_ms": 944_175, "duration_ms": 215_880, "title": "b"},
    ]


class SegmentTests(unittest.TestCase):
    def test_offsets_total_and_gap(self) -> None:
        segments, total, gaps = mh.build_segments(fake_clips())
        self.assertEqual([s["offset_ms"] for s in segments], [0, 372_369])
        self.assertEqual(total, 588_249)
        self.assertEqual(gaps, [282_431])
        self.assertEqual(segments[1]["end_ms"], 1_160_055)

    def test_overlapping_clips_are_rejected(self) -> None:
        clips = fake_clips()
        clips[1]["start_ms"] = 500_000
        with self.assertRaises(RuntimeError):
            mh.build_segments(clips)

    def test_expressions(self) -> None:
        segments, _, _ = mh.build_segments(fake_clips())
        select, offset, read_s = mh.build_expressions(segments)
        self.assertEqual(
            select,
            "between(t,0.000,372.369)+between(t,654.800,870.680)",
        )
        self.assertEqual(offset, "gte(T,654.800)*282.431")
        self.assertAlmostEqual(read_s, 870.680)

    def test_human_duration(self) -> None:
        self.assertEqual(mh.human_duration(282_431), "4m43s")
        self.assertEqual(mh.human_duration(0), "0m00s")


class SubtitleRemapTests(unittest.TestCase):
    @unittest.skipUnless(RESULT.exists(), "merged result not present")
    def test_real_clip_subtitles_remap(self) -> None:
        data, clips = mh.load_accepted(RESULT)
        rows, segments, total = mh.merge_subtitle_rows(clips)
        self.assertEqual(total, sum(c["duration_ms"] for c in clips))
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows[0][0], 0)
        # first cue of the second clip starts exactly at the first clip's duration
        second = [r for r in rows if r[0] >= segments[1]["offset_ms"]]
        self.assertEqual(second[0][0], segments[1]["offset_ms"])
        self.assertEqual(max(r[1] for r in rows), total)
        self.assertTrue(all(0 <= s < e <= total for s, e, _, _ in rows))
        for left, right in zip(rows, rows[1:]):
            self.assertLessEqual(left[0], right[0])


class ArtifactTests(unittest.TestCase):
    @unittest.skipUnless(RESULT.exists(), "merged result not present")
    def test_merged_result_and_streams(self) -> None:
        data = json.loads(RESULT.read_text(encoding="utf-8"))
        merge = data.get("merge")
        if merge is None:
            self.skipTest("result.json has no legacy merge block (pipeline uses assembly)")
        self.assertEqual(merge["status"], "SUCCESS")
        output = mh.resolve(merge["output"])
        self.assertTrue(output.exists(), output)
        info = ac.probe_source(output)
        self.assertEqual(info["video_codec"], "h264")
        self.assertEqual(info["audio_codec"], "aac")
        self.assertLessEqual(
            abs(info["duration_ms"] - merge["expected_duration_ms"]),
            ac.DEFAULTS["duration_tolerance_ms"],
        )
        self.assertGreaterEqual(merge["skipped_ms"], 0)
        self.assertEqual(merge["skipped_human"], "4m43s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
