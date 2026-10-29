"""Serial-scheduling tests for scripts/run_pipeline.py (stdlib unittest).

These tests replace the four heavyweight services with recorders and assert
the invariant that matters: llama-server, CosyVoice and the QSV stages never
overlap, and the TTS overshoot repair reopens the LLM only *after* the TTS
process is gone.

Run:
    .venv/Scripts/python.exe scripts/test_run_pipeline.py
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_intro as gi  # noqa: E402
import resource_manager as rm  # noqa: E402
import run_pipeline as rp  # noqa: E402

COPY = {
    "intro_spoken_text": "Daytona 2026，Dylan Patel 现场实录。他拆解了 CPU 瓶颈的算力账。中英双语，来看原声。",
    "screen_title": "CPU 为何成为 AI 新瓶颈",
    "screen_subtitle": "Dylan Patel · SemiAnalysis，2026",
}
TIMELINE = {"duration_ms": 9200, "lead_ms": 200, "voice_ms": 8800, "tail_ms": 200}
VOICE = {"text": COPY["intro_spoken_text"], "path": "n.wav", "final_seconds": 8.8,
         "raw_seconds": 8.9, "tempo": 1.0}


def make_args(**overrides: object) -> argparse.Namespace:
    base = dict(
        video_id="vid", title="t", summary="s", copy_json=None, copy_source="llm",
        spoken_text="", screen_title="", screen_subtitle="", voice_wav=None,
        renderer="auto", browser=None, series="AI 基建", speaker="SPEAKER",
        source="SOURCE", stamp="STAMP", stamp_right="STAMP-R", index="021",
        eyebrow="CONTEXT", eyebrow_right="FIELD RECORD", max_voice_repairs=2,
        reanalyze=False, srt=None, video=None,
        render_clips=False, skip_assembly=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def make_cfg() -> dict:
    return {**gi.DEFAULTS, "accent": "#ff5500"}


class Recorder:
    """Context manager that enforces one heavyweight process at a time."""

    def __init__(self, name: str, state: dict) -> None:
        self.name = name
        self.state = state

    def __enter__(self) -> "Recorder":
        if self.state["active"]:
            raise AssertionError(f"overlap: {self.state['active']} still alive when "
                                 f"{self.name} started")
        self.state["active"].add(self.name)
        self.state["events"].append(f"enter:{self.name}")
        return self

    def __exit__(self, *exc: object) -> bool:
        self.state["active"].discard(self.name)
        self.state["events"].append(f"exit:{self.name}")
        return False


class SerialPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="rp-test-")
        self.dir = Path(self.tmp.name)
        self.intro_dir = self.dir / "intro"
        self.intro_dir.mkdir()
        self.state: dict = {"active": set(), "events": []}
        self.args = make_args()
        self.cfg = make_cfg()

        self.patches = [
            mock.patch.object(rm, "llama_server",
                              side_effect=lambda **kw: Recorder("llama", self.state)),
            mock.patch.object(rm, "cosyvoice",
                              side_effect=lambda **kw: Recorder("cosyvoice", self.state)),
            mock.patch.object(rm, "quiet_stage",
                              side_effect=lambda name, **kw:
                              Recorder(f"quiet:{name}", self.state)),
            mock.patch.object(gi, "stage_copy", side_effect=self.fake_copy),
            mock.patch.object(gi, "stage_voice", side_effect=self.fake_voice),
            mock.patch.object(gi, "stage_picture", side_effect=self.fake_picture),
            mock.patch.object(gi, "stage_render", side_effect=self.fake_render),
            mock.patch.object(gi, "stage_rewrite", side_effect=self.fake_rewrite),
            mock.patch.object(gi, "save_copy",
                              side_effect=lambda _d, info, copy: {**info, **copy}),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    # -- fakes -----------------------------------------------------------
    def fake_copy(self, **kwargs: object) -> dict:
        self.state["events"].append("run:copy")
        return {"copy": dict(COPY), "info": {"source": "llm", "model": "fake"}}

    def fake_voice(self, **kwargs: object) -> dict:
        self.state["events"].append("run:voice")
        return {"voice": dict(VOICE), "timeline": dict(TIMELINE)}

    def fake_rewrite(self, **kwargs: object) -> dict:
        self.state["events"].append("run:rewrite")
        return {"copy": {**COPY, "intro_spoken_text":
                         "Daytona 2026，Dylan Patel 现场实录。他拆解了 CPU 的算力账。中英双语，来看原声。"}}

    def fake_picture(self, **kwargs: object) -> dict:
        self.state["events"].append("run:picture")
        return {"mode": "keyframes", "frames": [], "png": Path("x.png"),
                "payload": {"mode": "keyframes", "frames": []}}

    def fake_render(self, **kwargs: object) -> dict:
        self.state["events"].append("run:render")
        return {"status": "SUCCESS", "path": "intro.mp4", "duration_ms": 9200}

    # -- tests -----------------------------------------------------------
    def test_stages_never_overlap(self) -> None:
        rp.run_intro_stages(self.args, self.cfg, self.intro_dir)
        self.assertEqual(self.state["events"], [
            "enter:llama", "run:copy", "exit:llama",
            "enter:cosyvoice", "run:voice", "exit:cosyvoice",
            "enter:quiet:stage 3 picture", "run:picture", "exit:quiet:stage 3 picture",
            "enter:quiet:stage 4 media", "run:render", "exit:quiet:stage 4 media",
        ])
        self.assertEqual(self.state["active"], set())

    def test_tts_overshoot_reopens_llm_only_after_tts_exit(self) -> None:
        calls = {"voice": 0}

        def voice(**kwargs: object) -> dict:
            calls["voice"] += 1
            self.state["events"].append(f"run:voice{calls['voice']}")
            if calls["voice"] == 1:
                raise gi.VoiceWindowError("too long", voice_ms=9800, raw_seconds=9.8,
                                          final_seconds=9.8, tempo=1.15)
            return {"voice": dict(VOICE), "timeline": dict(TIMELINE)}

        with mock.patch.object(gi, "stage_voice", side_effect=voice):
            result = rp.run_intro_stages(self.args, self.cfg, self.intro_dir,
                                         max_voice_repairs=1)
        events = self.state["events"]
        self.assertEqual(events[:8], [
            "enter:llama", "run:copy", "exit:llama",
            "enter:cosyvoice", "run:voice1", "exit:cosyvoice",
            "enter:llama", "run:rewrite",
        ])
        self.assertIn("enter:cosyvoice", events[8:])
        # the repair rewrote the copy that stage 2 then synthesized
        self.assertEqual(result["copy"]["intro_spoken_text"],
                         "Daytona 2026，Dylan Patel 现场实录。他拆解了 CPU 的算力账。"
                         "中英双语，来看原声。")
        self.assertEqual(self.state["active"], set())

    def test_overshoot_beyond_repairs_fails_cleanly(self) -> None:
        with mock.patch.object(
                gi, "stage_voice",
                side_effect=gi.VoiceWindowError("too long", voice_ms=12000,
                                                raw_seconds=12.0)):
            with self.assertRaises(gi.VoiceWindowError):
                rp.run_intro_stages(self.args, self.cfg, self.intro_dir,
                                    max_voice_repairs=0)
        self.assertEqual(self.state["active"], set())

    def test_failed_picture_stage_does_not_reach_stage_four(self) -> None:
        with mock.patch.object(gi, "stage_picture",
                               side_effect=gi.StageError("no browser")):
            with self.assertRaises(gi.StageError):
                rp.run_intro_stages(self.args, self.cfg, self.intro_dir)
        events = self.state["events"]
        self.assertNotIn("enter:quiet:stage 4 media", events)
        self.assertEqual(self.state["active"], set())

    def test_pipeline_json_records_every_stage(self) -> None:
        pipeline = rp.Pipeline("vid", self.dir / "pipeline.json")
        rp.run_intro_stages(self.args, self.cfg, self.intro_dir, pipeline=pipeline)
        pipeline.finish({"heavy": []})
        data = json.loads((self.dir / "pipeline.json").read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual([s["status"] for s in data["stages"]],
                         ["SUCCESS"] * 4)
        self.assertEqual([s["key"] for s in data["stages"]],
                         ["LLM", "TTS", "PICTURE", "MEDIA"])


class AnalysisHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="rp-hook-")
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.cfg = make_cfg()

    def test_reuses_existing_analysis_without_calling_the_model(self) -> None:
        (self.dir / "analysis.json").write_text("{}", encoding="utf-8")
        hook = rp._analysis_hook(make_args(reanalyze=False), self.cfg, self.dir)
        with mock.patch.object(rp.subprocess, "run") as run:
            result = hook()
        run.assert_not_called()
        self.assertEqual(result["status"], "REUSED")

    def test_missing_analysis_without_srt_is_an_error(self) -> None:
        hook = rp._analysis_hook(make_args(reanalyze=True, srt=None), self.cfg, self.dir)
        with self.assertRaises(gi.StageError):
            hook()

    def test_media_hook_can_skip_assembly(self) -> None:
        hook = rp._media_hook(make_args(skip_assembly=True), self.dir)
        self.assertEqual(hook({}), {"assembly": "SKIPPED"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
