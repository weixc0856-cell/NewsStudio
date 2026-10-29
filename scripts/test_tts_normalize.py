"""Tests for TTS year normalization (stdlib unittest).

Run:
    .venv/Scripts/python.exe scripts/test_tts_normalize.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_intro as gi  # noqa: E402
import synthesize_dub as sd  # noqa: E402


class NormalizeTests(unittest.TestCase):
    def test_year_is_read_digit_by_digit(self) -> None:
        self.assertIn("二零二六年", sd.normalize_for_tts("Daytona 2026，现场实录。"))

    def test_existing_nian_is_absorbed(self) -> None:
        out = sd.normalize_for_tts("2026 年 Daytona 大会")
        self.assertEqual(out, "二零二六年 Daytona 大会")

    def test_other_years(self) -> None:
        self.assertEqual(sd.normalize_for_tts("2019"), "二零一九年")
        self.assertEqual(sd.normalize_for_tts("1998 年"), "一九九八年")

    def test_embedded_number_is_untouched(self) -> None:
        self.assertEqual(sd.normalize_for_tts("12026 台机器"), "12026 台机器")

    def test_non_year_number_is_untouched(self) -> None:
        self.assertEqual(sd.normalize_for_tts("GPT-5.4"), "GPT-5.4")

    def test_idempotent(self) -> None:
        once = sd.normalize_for_tts("2026")
        self.assertEqual(sd.normalize_for_tts(once), once)

    def test_tts_request_normalizes_the_payload(self) -> None:
        response = mock.Mock(status_code=200, content=b"RIFF")
        with mock.patch.object(sd.requests, "post", return_value=response) as post:
            sd.tts_request("http://x", "Daytona 2026", None, None, 10)
        payload = post.call_args.kwargs["json"]
        self.assertIn("二零二六年", payload["text"])
        self.assertNotIn("2026", payload["text"])

    def test_tts_request_passes_preset_speaker(self) -> None:
        response = mock.Mock(status_code=200, content=b"RIFF")
        with mock.patch.object(sd.requests, "post", return_value=response) as post:
            sd.tts_request("http://x", "你好", None, None, 10, speaker="中文男")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["speaker"], "中文男")
        self.assertNotIn("prompt_wav", payload)


class IntroVoiceTests(unittest.TestCase):
    def test_synthesize_voice_sends_and_records_normalized_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {**gi.DEFAULTS, "voice_speaker": ""}   # zero-shot path
            with mock.patch.object(sd, "wait_for_service",
                                   return_value={"model_class": "fake"}),                  mock.patch.object(sd, "tts_request",
                                   return_value=b"RIFF") as tts,                  mock.patch.object(sd, "probe_duration", return_value=8.0),                  mock.patch.object(gi, "pad_head"):
                info = gi.synthesize_voice(text="Daytona 2026，现场实录。",
                                           out_dir=Path(tmp), cfg=cfg)
        sent = tts.call_args.args[1]
        self.assertIn("二零二六年", sent)
        self.assertIn("二零二六年", info["tts_text"])
        self.assertEqual(info["text"], "Daytona 2026，现场实录。")

    def test_synthesize_voice_uses_preset_speaker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {**gi.DEFAULTS, "voice_speaker": "中文男"}
            with mock.patch.object(sd, "wait_for_service",
                                   return_value={"model_class": "fake"}),                  mock.patch.object(sd, "tts_request",
                                   return_value=b"RIFF") as tts,                  mock.patch.object(sd, "probe_duration", return_value=8.0),                  mock.patch.object(gi, "pad_head"):
                info = gi.synthesize_voice(text="Daytona 2026，现场实录。",
                                           out_dir=Path(tmp), cfg=cfg)
        self.assertEqual(tts.call_args.kwargs["speaker"], "中文男")
        self.assertEqual(tts.call_args.args[2], "")      # no reference audio is sent
        self.assertEqual(info["voice_speaker"], "中文男")
        self.assertEqual(info["prompt_wav"], "")

    def test_default_intro_voice_is_the_preset_female(self) -> None:
        self.assertEqual(gi.DEFAULTS["voice_speaker"], "中文女")

    def test_synthesize_voice_pads_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {**gi.DEFAULTS, "voice_speaker": "中文男"}
            with mock.patch.object(sd, "wait_for_service",
                                   return_value={"model_class": "fake"}),                  mock.patch.object(sd, "tts_request", return_value=b"RIFF"),                  mock.patch.object(sd, "probe_duration", return_value=8.0),                  mock.patch.object(gi, "pad_head") as pad:
                info = gi.synthesize_voice(text="测试。", out_dir=Path(tmp), cfg=cfg)
        self.assertEqual(pad.call_args.args[1], 600)
        self.assertEqual(info["head_silence_ms"], 600)

    def test_stage_voice_zeroes_lead_for_padded_audio(self) -> None:
        voice = {"final_seconds": 9.205, "raw_seconds": 8.605, "tempo": 1.15,
                 "head_silence_ms": 600, "path": "narration.wav"}
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(gi, "synthesize_voice", return_value=voice):
                out = gi.stage_voice(out_dir=Path(tmp), cfg={**gi.DEFAULTS}, text="测试。")
        self.assertEqual(out["timeline"]["lead_ms"], 0)
        self.assertEqual(out["timeline"]["voice_ms"], 9205)
        self.assertEqual(out["timeline"]["duration_ms"], 10_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
