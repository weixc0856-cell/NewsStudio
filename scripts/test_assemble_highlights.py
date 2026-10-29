"""Tests for scripts/assemble_highlights.py (stdlib unittest only).

Run:
    .venv/Scripts/python.exe scripts/test_assemble_highlights.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assemble_highlights as ah  # noqa: E402
import auto_clip as ac  # noqa: E402

RESULT = ac.ROOT / "clips" / "c88l8daXiv4" / "result.json"
INTRO = ac.ROOT / "clips" / "c88l8daXiv4" / "intro" / "intro.json"

INTRO_MS = 9000
TRANSITION_MS = 500


def fake_clips() -> list[dict]:
    return [
        {"index": 1, "start_ms": 289_375, "duration_ms": 372_369, "title": "a"},
        {"index": 2, "start_ms": 944_175, "duration_ms": 215_880, "title": "b"},
    ]


def real_clips() -> list[dict]:
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    clips = [c for c in data["clips"] if c["acceptance"]["passed"]]
    clips.sort(key=lambda c: c["start_ms"])
    return clips


def test_cfg() -> dict:
    return {**ah.DEFAULTS, "transition_ms": TRANSITION_MS}


class TimelineTests(unittest.TestCase):
    def test_order_offsets_total_and_gap(self) -> None:
        segments, total, gaps = ah.build_timeline(fake_clips(), INTRO_MS, TRANSITION_MS)
        self.assertEqual([s["kind"] for s in segments],
                         ["intro", "clip", "transition", "clip"])
        self.assertEqual([s["offset_ms"] for s in segments],
                         [0, 9_000, 381_369, 381_869])
        self.assertEqual(total, 597_749)
        self.assertEqual(gaps, [282_431])
        self.assertEqual(segments[-1]["end_ms"], total)

    def test_clip_end_is_second_clip_end_plus_intro_and_card(self) -> None:
        segments, total, _ = ah.build_timeline(fake_clips(), INTRO_MS, TRANSITION_MS)
        last = segments[-1]
        self.assertEqual(last["source_end_ms"], 1_160_055)
        self.assertEqual(last["offset_ms"] - INTRO_MS - TRANSITION_MS,
                         fake_clips()[0]["duration_ms"])

    def test_overlap_is_rejected(self) -> None:
        clips = fake_clips()
        clips[1]["start_ms"] = 500_000
        with self.assertRaises(ValueError):
            ah.build_timeline(clips, INTRO_MS, TRANSITION_MS)

    def test_single_clip_has_no_transition(self) -> None:
        segments, total, gaps = ah.build_timeline(fake_clips()[:1], INTRO_MS, TRANSITION_MS)
        self.assertEqual([s["kind"] for s in segments], ["intro", "clip"])
        self.assertEqual(total, INTRO_MS + 372_369)
        self.assertEqual(gaps, [])

    def test_human_duration(self) -> None:
        self.assertEqual(ah.human_duration(282_431), "4m43s")
        self.assertEqual(ah.human_duration(0), "0m00s")


class SubtitleTests(unittest.TestCase):
    @unittest.skipUnless(RESULT.exists(), "episode 21 result not present")
    def test_real_clip_subtitles_remap(self) -> None:
        clips = real_clips()
        rows, segments, total = ah.subtitle_rows(clips, INTRO_MS, TRANSITION_MS)
        expected = INTRO_MS + sum(c["duration_ms"] for c in clips)             + TRANSITION_MS * (len(clips) - 1)
        self.assertEqual(total, expected)
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows[0][0], INTRO_MS)
        second = [r for r in rows if r[0] >= segments[1]["offset_ms"]]
        self.assertEqual(second[0][0], INTRO_MS + clips[0]["duration_ms"] + TRANSITION_MS)
        self.assertLessEqual(max(r[1] for r in rows), total)
        self.assertTrue(all(0 <= s < e <= total for s, e, _, _ in rows))
        for left, right in zip(rows, rows[1:]):
            self.assertLessEqual(left[0], right[0])

    @unittest.skipUnless(RESULT.exists(), "episode 21 result not present")
    def test_first_cue_is_the_whole_cue_51(self) -> None:
        cues, errors = ac.parse_bilingual_srt(
            ac.ROOT / "subtitles" / "c88l8daXiv4.zh.bilingual.srt")
        self.assertEqual(errors, [])
        # the first cue of the current clip 1 must not be a dependent start
        clips = real_clips()
        start = clips[0]["start_ms"]
        cue = next(c for c in cues if c.start == start)
        self.assertFalse(ac.DEPENDENT_START.match(cue.top.strip()))
        self.assertTrue(cues[50].top.startswith("right to exist"))


class GraphTests(unittest.TestCase):
    def test_graph_has_four_way_concat_and_fades(self) -> None:
        clips = fake_clips()
        graph = ah.build_filter_complex(
            clips=clips, intro_ms=INTRO_MS, transition_ms=TRANSITION_MS,
            ass_path=ac.ROOT / "clips" / "x" / "work" / "assembly.ass", cfg=test_cfg())
        self.assertIn("concat=n=4:v=1:a=0", graph)
        self.assertIn("concat=n=4:v=0:a=1", graph)
        self.assertIn("between(t,0.000,372.369)", graph)
        self.assertIn("between(t,654.800,870.680)", graph)
        self.assertIn("afade=t=out", graph)
        self.assertIn("afade=t=in", graph)
        self.assertIn("anullsrc", graph)
        self.assertIn("ass=clips/x/work/assembly.ass", graph)

    def test_ffmpeg_command_order(self) -> None:
        cmd = ah.build_ffmpeg_cmd(
            intro=ac.ROOT / "clips/x/intro/intro.mp4",
            source=ac.ROOT / "downloads/src.mkv",
            card=ac.ROOT / "clips/x/work/transition.png",
            out=ac.ROOT / "clips/x/work/out.mp4",
            clips=fake_clips(), intro_ms=INTRO_MS, transition_ms=TRANSITION_MS,
            ass_path=ac.ROOT / "clips/x/work/assembly.ass", cfg=test_cfg())
        self.assertEqual(cmd[cmd.index("-ss") + 1], "289.375")
        self.assertEqual(cmd[cmd.index("-t", cmd.index("-ss")) + 1], "871.180")
        self.assertEqual(cmd[cmd.index("-c:v") + 1], "h264_qsv")
        self.assertEqual(cmd[cmd.index("-c:a") + 1], "aac")
        self.assertIn("-loop", cmd)
        self.assertIn("-map_chapters", cmd)


class TransitionTests(unittest.TestCase):
    def test_dip_to_black_defaults(self) -> None:
        self.assertEqual(ah.DEFAULTS["card_fade_ms"], 100)
        self.assertEqual(ah.DEFAULTS["fade_ms"], 200)

    def test_card_and_audio_fades_in_graph(self) -> None:
        graph = ah.build_filter_complex(
            clips=fake_clips(), intro_ms=INTRO_MS, transition_ms=TRANSITION_MS,
            ass_path=ac.ROOT / "clips" / "x" / "work" / "assembly.ass",
            cfg=test_cfg())
        self.assertIn("fade=t=in:st=0:d=0.100", graph)
        self.assertIn("fade=t=out:st=0.400:d=0.100", graph)
        self.assertIn("afade=t=out", graph)


class BedTests(unittest.TestCase):
    def test_bed_plan_uses_preroll(self) -> None:
        bed = ah.bed_plan(fake_clips(), 9000)
        self.assertTrue(bed["enabled"])
        self.assertEqual(bed["start_ms"], 280_375)
        self.assertEqual(bed["duration_ms"], 9_000)
        self.assertEqual(bed["volume"], 0.15)
        self.assertEqual(bed["fade_out_ms"], 400)

    def test_graph_with_bed_mixes_preroll(self) -> None:
        graph = ah.build_filter_complex(
            clips=fake_clips(), intro_ms=INTRO_MS, transition_ms=TRANSITION_MS,
            ass_path=ac.ROOT / "clips" / "x" / "work" / "assembly.ass",
            cfg=test_cfg(), bed=True)
        self.assertIn("[3:a]", graph)
        self.assertIn("[ai0mix]", graph)
        self.assertIn("volume=0.15", graph)
        self.assertIn("afade=t=out", graph)

    def test_command_includes_bed_input(self) -> None:
        bed = ah.bed_plan(fake_clips(), INTRO_MS)
        cmd = ah.build_ffmpeg_cmd(
            intro=ac.ROOT / "clips/x/intro/intro.mp4",
            source=ac.ROOT / "downloads/src.mkv",
            card=ac.ROOT / "clips/x/work/transition.png",
            out=ac.ROOT / "clips/x/work/out.mp4",
            clips=fake_clips(), intro_ms=INTRO_MS, transition_ms=TRANSITION_MS,
            ass_path=ac.ROOT / "clips/x/work/assembly.ass", cfg=test_cfg(), bed=bed)
        self.assertEqual(cmd.count("-ss"), 2)
        self.assertIn(f"{bed['start_ms'] / 1000:.3f}", cmd)


class ArtifactTests(unittest.TestCase):
    @unittest.skipUnless(RESULT.exists() and INTRO.exists(), "episode 21 artifacts absent")
    def test_assembly_result_and_streams(self) -> None:
        data = json.loads(RESULT.read_text(encoding="utf-8"))
        assembly = data.get("assembly")
        self.assertIsNotNone(assembly, "result.json has no assembly block")
        self.assertEqual(assembly["status"], "SUCCESS")
        output = ah.resolve(assembly["output"])
        self.assertTrue(output.exists(), output)
        info = ac.probe_source(output)
        self.assertEqual(info["video_codec"], "h264")
        self.assertEqual(info["audio_codec"], "aac")
        self.assertLessEqual(abs(info["duration_ms"] - assembly["expected_duration_ms"]),
                             ah.DEFAULTS["duration_tolerance_ms"])
        self.assertEqual(assembly["skipped_human"],
                         ah.human_duration(assembly["skipped_ms"]))
        self.assertTrue(assembly["bed"]["enabled"])
        self.assertEqual(assembly["bed"]["volume"], 0.15)
        self.assertEqual(assembly["bed"]["fade_out_ms"], 400)
        self.assertEqual(assembly["transition"]["duration_ms"], 500)
        self.assertGreaterEqual(assembly["intro"]["duration_ms"],
                                ah.DEFAULTS["min_intro_ms"])
        self.assertLessEqual(assembly["intro"]["duration_ms"],
                             ah.DEFAULTS["max_intro_ms"])
        self.assertFalse(assembly["manual_review"])
        self.assertEqual(data["intro"]["status"], "SUCCESS")

    @unittest.skipUnless(RESULT.exists() and INTRO.exists(), "episode 21 artifacts absent")
    def test_intro_is_standalone_6_to_9_5_seconds(self) -> None:
        intro = json.loads(INTRO.read_text(encoding="utf-8"))
        self.assertEqual(intro["status"], "SUCCESS")
        self.assertTrue(intro["acceptance"]["passed"])
        self.assertTrue(6000 <= intro["duration_ms"] <= 9500)
        self.assertIn(intro["picture"]["renderer"], ("html", "poster"))
        self.assertIn(intro["picture"]["animation"], ("keyframes", "poster"))
        self.assertEqual(intro["animation"]["duration_ms"], intro["planned_duration_ms"])
        self.assertEqual(intro["copy"]["source"], "llm")
        self.assertTrue((ah.resolve(intro["path"])).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
