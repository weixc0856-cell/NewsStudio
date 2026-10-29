"""Tests for the static poster generator (stdlib unittest).

Run:
    .venv/Scripts/python.exe scripts/test_generate_poster.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_intro as gi  # noqa: E402
import generate_poster as gp  # noqa: E402


def values(**overrides: str) -> dict[str, str]:
    base = gp.poster_values(
        title_en="WHY CPU IS THE NEW AI BOTTLENECK",
        title_zh="CPU 为何成为 AI 新瓶颈",
        speaker="Dylan Patel", event="Daytona 2026",
        organization="SemiAnalysis", verification="3-source cross-check",
        summary_zh="强化学习与代码智能体把闭环压紧后，传统 x86 资源全面告罄。",
        insight_1="代码 Agent 吞吐提升 14 倍，执行编译吃空集群算力",
        insight_2="微软等云厂商备用 CPU 售罄，供电与网络拓扑重构",
        insight_3="数据中心重心从单纯 GPU 扩展转向异构协同调度",
        index="021", series="AI 基建 / 第 21 期")
    base.update(overrides)
    return base


class TemplateTests(unittest.TestCase):
    def test_template_renders_all_placeholders(self) -> None:
        html = gi.render_template(gi.INTRO_TEMPLATE, values())
        self.assertIn("WHY CPU IS THE NEW AI BOTTLENECK", html)
        self.assertIn("CPU 为何成为 AI 新瓶颈", html)
        for label in ("Speaker", "Source Event", "Organization", "Verification"):
            self.assertIn(label, html)
        self.assertIn("TECHNICAL HIGHLIGHTS", html)
        self.assertIn("KEY ENGINEERING INSIGHTS", html)
        self.assertIn("代码 Agent 吞吐提升 14 倍", html)
        self.assertIn("AI 基建 / 第 21 期", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("CONTEXT", html)
        self.assertNotIn("FIELD RECORD", html)
        self.assertNotIn("@keyframes", html)

    def test_values_are_html_escaped(self) -> None:
        data = gp.poster_values(title_en="A & B", title_zh="甲 & 乙", speaker="s",
                                event="e", organization="o", verification="v")
        self.assertIn("A &amp; B", data["TITLE_EN"])
        self.assertIn("甲 &amp; 乙", data["TITLE_ZH"])

    def test_missing_titles_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gp.poster_values(title_en="", title_zh="中文", speaker="s", event="e",
                             organization="o", verification="v")


class DurationTests(unittest.TestCase):
    def test_silent_defaults_to_five_seconds(self) -> None:
        plan = gp.plan_poster_duration(silent=True)
        self.assertEqual(plan["duration_ms"], 5000)
        self.assertEqual(plan["mode"], "short")

    def test_silent_full_mode(self) -> None:
        plan = gp.plan_poster_duration(silent=True, requested_ms=8000)
        self.assertEqual(plan["mode"], "full")

    def test_short_voice_is_padded_to_four_seconds(self) -> None:
        plan = gp.plan_poster_duration(silent=False, voice_ms=3000)
        self.assertEqual(plan["duration_ms"], 4000)
        self.assertEqual(plan["mode"], "short")

    def test_full_voice(self) -> None:
        plan = gp.plan_poster_duration(silent=False, voice_ms=8800)
        self.assertEqual(plan["duration_ms"], 9250)
        self.assertEqual(plan["mode"], "full")

    def test_voice_beyond_cap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gp.plan_poster_duration(silent=False, voice_ms=9500)

    def test_classify(self) -> None:
        self.assertEqual(gp.classify(6000), "short")
        self.assertEqual(gp.classify(6500), "standard")
        self.assertEqual(gp.classify(7000), "full")


class CommandTests(unittest.TestCase):
    def test_static_command_has_no_animation(self) -> None:
        cmd = gp.build_poster_command(png=Path("p.png"), out=Path("o.mp4"),
                                      duration_ms=5000, voice=None)
        text = " ".join(cmd)
        self.assertIn("-frames:v", cmd)
        self.assertEqual(cmd[cmd.index("-frames:v") + 1], "300")
        self.assertEqual(cmd[cmd.index("-r") + 1], "60")
        self.assertIn("fps=60,format=yuv420p", text)
        for banned in ("zoompan", "xfade", "drawbox", "fade=t="):
            self.assertNotIn(banned, text)

    def test_voice_command_delays_audio(self) -> None:
        cmd = gp.build_poster_command(png=Path("p.png"), out=Path("o.mp4"),
                                      duration_ms=9250, voice=Path("v.wav"))
        text = " ".join(cmd)
        self.assertIn("adelay=200|200", text)
        self.assertIn("alimiter", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
