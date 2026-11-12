"""Tests for dub_mix.py (stdlib unittest only, no ffmpeg required).

Run:
    .venv/Scripts/python.exe scripts/test_dub_mix.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dub_mix  # noqa: E402
import auto_clip as ac  # noqa: E402


class FilterGraphTests(unittest.TestCase):
    def test_graph_uses_sidechaincompress_and_amix(self) -> None:
        graph = dub_mix.build_filter_complex(None)
        self.assertIn("sidechaincompress", graph)
        self.assertIn("amix=inputs=2", graph)
        self.assertIn("asplit=2[dub_side][dub_mix]", graph)
        self.assertIn("[ducked][dub_mix]", graph)
        self.assertNotIn("ass=", graph)
        self.assertTrue(graph.endswith("[aout]"))

    def test_graph_burns_ass_when_given(self) -> None:
        ass = Path(tempfile.gettempdir()) / "subs" / "clip-01.ass"
        graph = dub_mix.build_filter_complex(ass)
        self.assertIn("[0:v]ass=", graph)
        self.assertIn("[v]", graph)
        # Windows drive letter must be escaped inside the filter argument.
        escaped = str(ass).replace("\\", "/").replace(":", "\\:")
        self.assertIn(escaped, graph)

    def test_parameters_are_rendered(self) -> None:
        graph = dub_mix.build_filter_complex(None, {"duck_ratio": 12.5,
                                                   "attack_ms": 5, "release_ms": 250,
                                                   "sample_rate": 44100})
        self.assertIn("ratio=12.5", graph)
        self.assertIn("attack=5", graph)
        self.assertIn("release=250", graph)
        self.assertIn("aresample=44100", graph)

    def test_bed_filter_emits_only_ducked_original(self) -> None:
        graph = dub_mix.build_bed_filter({})
        self.assertIn("[ducked]", graph)
        self.assertNotIn("[aout]", graph)
        self.assertNotIn("amix", graph)

    def test_ffmpeg_cmd_dub_input_and_audio_map(self) -> None:
        cmd = dub_mix.build_ffmpeg_cmd(Path("a.mp4"), Path("b.wav"), Path("c.mp4"),
                                       Path("d.ass"), {"qsv_quality": 17})
        self.assertEqual(cmd[0], "ffmpeg")
        first = cmd.index("-i")
        second = cmd.index("-i", first + 1)
        self.assertEqual(cmd[first + 1], "a.mp4")
        self.assertEqual(cmd[second + 1], "b.wav")
        self.assertIn("-map", cmd)
        self.assertIn("[aout]", cmd)
        self.assertIn("17", cmd)

    def test_ffmpeg_cmd_without_ass_maps_source_video(self) -> None:
        cmd = dub_mix.build_ffmpeg_cmd(Path("a.mp4"), Path("b.wav"), Path("c.mp4"))
        self.assertIn("0:v:0", cmd)
        self.assertNotIn("[v]", cmd)


class AutoClipIntegrationTests(unittest.TestCase):
    """render_clip must switch to filter_complex when a dub track is given."""

    def _cfg(self) -> dict:
        return {"qsv_quality": 19, "audio_codec": "aac", "audio_bitrate": "160k",
                "margin_v": 100, "cfr": "off", "duck_threshold": 0.02,
                "duck_target_db": -21.5, "duck_ratio": 20.0, "attack_ms": 15,
                "release_ms": 400, "dub_gain": 1.0, "sample_rate": 48000}

    def _render(self, dub):
        captured: dict[str, list[str]] = {}

        def fake_run(cmd, timeout, log_path=None):
            captured["cmd"] = cmd
            return type("P", (), {"returncode": 0, "stderr": ""})()

        original = ac.run_cmd
        ac.run_cmd = fake_run
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                ac.render_clip(Path("source.mp4"),
                               {"start_ms": 1000, "duration_ms": 5000},
                               [(0, 2000, "top", "bottom")], self._cfg(), tmp_path, 1,
                               {"vfr": False, "fps": "30"}, dub)
        finally:
            ac.run_cmd = original
        return captured["cmd"]

    def test_dub_branch_uses_filter_complex_and_two_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dub = Path(tmp) / "clip-01.wav"
            dub.write_bytes(b"\0" * 64)
            cmd = self._render(dub)
        self.assertIn("-filter_complex", cmd)
        self.assertIn("[aout]", cmd)
        self.assertEqual(cmd.count("-i"), 2)
        self.assertNotIn("-vf", cmd)

    def test_no_dub_keeps_legacy_vf_path(self) -> None:
        cmd = self._render(None)
        self.assertIn("-vf", cmd)
        self.assertNotIn("-filter_complex", cmd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
