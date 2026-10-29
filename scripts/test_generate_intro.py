"""Deterministic-logic tests for scripts/generate_intro.py (stdlib unittest).

Run:
    .venv/Scripts/python.exe scripts/test_generate_intro.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_intro as gi  # noqa: E402

VALID_COPY = {
    "intro_spoken_text": "Daytona 2026，Dylan Patel 现场实录。他拆解了 CPU 瓶颈的算力账。中英双语，来看原声。",
    "screen_title": "CPU 为何成为 AI 新瓶颈",
    "screen_subtitle": "Dylan Patel · SemiAnalysis，2026",
}

CHROME = {
    "series": "AI 基建 / 第 21 期",
    "speaker": "DYLAN PATEL / SEMIANALYSIS",
    "source": "SemiAnalysis × Daytona",
    "stamp": "FIELD RECORD / 2026",
    "stamp_right": "2026 / DATACENTER · CPU",
    "index": "021",
    "eyebrow": "CONTEXT",
    "eyebrow_right": "CPU / DATACENTER",
    "accent": "#ff5500",
}


class CopyTests(unittest.TestCase):
    def test_normalize_valid(self) -> None:
        copy = gi.normalize_copy(VALID_COPY)
        self.assertEqual(copy["screen_title"], VALID_COPY["screen_title"])
        self.assertEqual(gi._count_sentences(copy["intro_spoken_text"]), 3)

    def test_requires_exactly_three_sentences(self) -> None:
        with self.assertRaises(ValueError):
            gi.normalize_copy({**VALID_COPY, "intro_spoken_text": "第一句。第二句。"})

    def test_rejects_hype_words(self) -> None:
        with self.assertRaises(ValueError):
            gi.normalize_copy({**VALID_COPY, "screen_title": "震撼：CPU 为何成为 AI 新瓶颈"})

    def test_rejects_long_spoken_text(self) -> None:
        long_text = "这是一句用于测试超长文案的说明文字，包含更多信息。" * 3
        with self.assertRaises(ValueError):
            gi.normalize_copy({**VALID_COPY, "intro_spoken_text": long_text})

    def test_rejects_short_screen_title(self) -> None:
        with self.assertRaises(ValueError):
            gi.normalize_copy({**VALID_COPY, "screen_title": "CPU 瓶颈"})

    def test_extract_json_object_handles_fence(self) -> None:
        obj = gi._extract_json_object('```json\n{"intro_spoken_text": "a"}\n```')
        self.assertEqual(obj["intro_spoken_text"], "a")

    def test_copy_prompt_has_5w1h_and_examples(self) -> None:
        prompt = gi.build_copy_prompt("节目", "摘要")
        for token in ("Who + Where + When", "What + Why/How", "We did",
                      "intro_spoken_text", "screen_title", "screen_subtitle",
                      "反例", "正例", "Daytona 2026"):
            self.assertIn(token, prompt)

    def test_compress_prompt_keeps_original(self) -> None:
        prompt = gi.build_compress_prompt(VALID_COPY["intro_spoken_text"])
        self.assertIn(VALID_COPY["intro_spoken_text"], prompt)
        self.assertIn("intro_spoken_text", prompt)


class TimelineTests(unittest.TestCase):
    def test_preferred_tail(self) -> None:
        plan = gi.plan_timeline(7500)
        self.assertEqual(plan, {"duration_ms": 7950, "lead_ms": 200,
                                "voice_ms": 7500, "tail_ms": 250})

    def test_tail_shrinks_before_cap(self) -> None:
        plan = gi.plan_timeline(9100)
        self.assertEqual(plan["duration_ms"], 9400)
        self.assertEqual(plan["tail_ms"], 100)

    def test_plan_leaves_encoder_headroom(self) -> None:
        plan = gi.plan_timeline(9140)
        self.assertEqual(plan["duration_ms"], 9440)
        self.assertLessEqual(plan["duration_ms"],
                             gi.DEFAULTS["max_duration_ms"] - gi.DEFAULTS["duration_guard_ms"])
        with self.assertRaises(ValueError):
            gi.plan_timeline(9150)

    def test_impossible_voice_raises(self) -> None:
        with self.assertRaises(ValueError):
            gi.plan_timeline(9500)

    def test_short_voice_is_padded_to_six_seconds(self) -> None:
        plan = gi.plan_timeline(3000)
        self.assertEqual(plan["duration_ms"], 6000)
        self.assertEqual(plan["tail_ms"], 2800)

    def test_tempo(self) -> None:
        self.assertEqual(gi.tempo_for(8800), 1.0)
        self.assertAlmostEqual(gi.tempo_for(9200), 9200 / 8800)
        self.assertEqual(gi.tempo_for(12000), gi.DEFAULTS["max_tempo"])

    def test_window_and_fps(self) -> None:
        self.assertEqual(gi.DEFAULTS["min_duration_ms"], 6000)
        self.assertEqual(gi.DEFAULTS["max_duration_ms"], 9500)
        self.assertEqual(gi.DEFAULTS["fps"], 60)


class StageTests(unittest.TestCase):
    def test_voice_window_error_reports_measured_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "v.wav"
            wav.write_bytes(b"x")
            with mock.patch.object(gi.sd, "probe_duration", return_value=12.0):
                with self.assertRaises(gi.VoiceWindowError) as ctx:
                    gi.stage_voice(out_dir=Path(tmp), cfg=gi.DEFAULTS, text="x",
                                   voice_wav=wav)
            self.assertEqual(ctx.exception.voice_ms, 12000)

    def test_voice_stage_writes_narration_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "v.wav"
            wav.write_bytes(b"x")
            with mock.patch.object(gi.sd, "probe_duration", return_value=8.0):
                result = gi.stage_voice(out_dir=Path(tmp), cfg=gi.DEFAULTS, text="x",
                                        voice_wav=wav)
            self.assertEqual(result["timeline"]["duration_ms"], 8450)
            saved = json.loads((Path(tmp) / "narration.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["final_seconds"], 8.0)


class PosterConfigTests(unittest.TestCase):
    def test_poster_voice_budget_targets_seven_to_nine_seconds(self) -> None:
        args = gi.parse_args(["--video-id", "x", "--intro-style", "poster"])
        cfg = gi.build_cfg(args)
        self.assertEqual(cfg["voice_budget_ms"], 8500)
        plan = gi.plan_timeline(8500, cfg)
        self.assertEqual(plan["duration_ms"], 8950)
        self.assertLessEqual(plan["duration_ms"], 9000)

    def test_classic_keeps_the_default_budget(self) -> None:
        args = gi.parse_args(["--video-id", "x", "--intro-style", "classic"])
        self.assertEqual(gi.build_cfg(args)["voice_budget_ms"], 8800)


class TemplateTests(unittest.TestCase):
    def test_templates_exist(self) -> None:
        self.assertTrue((gi.TEMPLATE_DIR / "intro.html").is_file())
        self.assertTrue((gi.TEMPLATE_DIR / "transition.html").is_file())

    def test_state_zero_and_one(self) -> None:
        html0 = gi.build_intro_html(copy=VALID_COPY, chrome=CHROME, state=0)
        html1 = gi.build_intro_html(copy=VALID_COPY, chrome=CHROME, state=1)
        self.assertIn('data-state="0"', html0)
        self.assertIn('data-state="1"', html1)
        self.assertNotIn("{{", html0)
        self.assertIn("CPU 为何成为 AI 新瓶颈", html1)

    def test_escapes_user_text(self) -> None:
        copy = {**VALID_COPY, "screen_title": "CPU <b> 新瓶颈"}
        html = gi.build_intro_html(copy=copy, chrome=CHROME, state=1)
        self.assertIn("CPU &lt;b&gt; 新瓶颈", html)
        self.assertNotIn("<b>", html)

    def test_unfilled_placeholder_guard(self) -> None:
        with self.assertRaises(ValueError):
            gi.render_template("intro.html", {"TITLE": "x"})

    def test_card_html(self) -> None:
        html = gi.build_card_html(index="02", title="AI 推理对硬件资源的冲击",
                                  series="AI 基建 / 第 21 期")
        self.assertNotIn("{{", html)
        self.assertIn("AI 推理对硬件资源的冲击", html)
        self.assertIn("02", html)


class AnimationTests(unittest.TestCase):
    def test_plan_animation(self) -> None:
        plan = gi.plan_animation(9256, 250)
        self.assertEqual(plan["bar_reveal_ms"], 550)
        self.assertEqual(plan["title_delay_ms"], 150)
        self.assertEqual(plan["title_fade_ms"], 550)
        self.assertEqual(plan["fade_out_ms"], 250)
        self.assertEqual(plan["ken_burns_per_sec"], 0.0005)

    def test_two_frame_command(self) -> None:
        cmd = gi.build_render_command(
            frames=[Path("a.png"), Path("b.png")], voice=Path("v.wav"),
            out=Path("o.mp4"),
            timeline={"duration_ms": 9256, "lead_ms": 200,
                      "voice_ms": 8806, "tail_ms": 250},
            animation=gi.plan_animation(9256, 250), cfg={**gi.DEFAULTS}, gain=1.0)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertEqual(graph.count("xfade="), 1)
        self.assertIn("offset=0.150", graph)
        self.assertIn("duration=0.550", graph)
        self.assertIn("zoompan", graph)
        self.assertIn("drawbox", graph)
        self.assertIn("color=0xff5500", graph)
        self.assertIn("[2:a]", graph)
        self.assertIn("-shortest", cmd)
        self.assertEqual(cmd[cmd.index("-r") + 1], "60")
        # 9256 ms -> 555 whole frames at 60 fps -> 9.250 s for both streams
        self.assertEqual(cmd[cmd.index("-frames:v") + 1], "555")
        self.assertIn("9.250000", cmd)

    def test_single_frame_fallback(self) -> None:
        cmd = gi.build_render_command(
            frames=[Path("a.png")], voice=Path("v.wav"), out=Path("o.mp4"),
            timeline={"duration_ms": 9256, "lead_ms": 200,
                      "voice_ms": 8806, "tail_ms": 250},
            animation=gi.plan_animation(9256, 250), cfg={**gi.DEFAULTS}, gain=1.0)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertNotIn("xfade", graph)
        self.assertIn("[1:a]", graph)
        self.assertIn("zoompan", graph)
        self.assertIn("drawbox", graph)


class ArtifactTests(unittest.TestCase):
    INTRO = gi.ROOT / "clips" / "c88l8daXiv4" / "intro" / "intro.json"

    @unittest.skipUnless(INTRO.exists(), "episode 21 intro not present")
    def test_intro_artifact(self) -> None:
        intro = json.loads(self.INTRO.read_text(encoding="utf-8"))
        self.assertEqual(intro["status"], "SUCCESS")
        self.assertTrue(6000 <= intro["duration_ms"] <= 9500)
        self.assertTrue(intro["acceptance"]["passed"])
        self.assertIn(intro["picture"]["animation"], ("keyframes", "poster"))
        self.assertEqual(intro["config"]["fps"], 60)
        self.assertEqual(intro["template"], "assets/templates/intro.html")
        self.assertEqual(intro["accent"], "#ff5500")
        self.assertEqual(intro["copy"]["source"], "llm")
        self.assertEqual(gi._count_sentences(intro["copy"]["intro_spoken_text"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
