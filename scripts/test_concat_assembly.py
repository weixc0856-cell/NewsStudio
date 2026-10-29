"""Unit tests for scripts/concat_assembly.py (stdlib unittest).

Run:
    .venv/Scripts/python.exe scripts/test_concat_assembly.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import concat_assembly as ca  # noqa: E402

CFG = {"width": 1920, "height": 1080, "fps": 60, "audio_bitrate": "160k",
       "qsv_quality": 19, "fade_ms": 250, "duration_tolerance_ms": 1500,
       "min_intro_ms": 6000, "max_intro_ms": 9500}


def spec(name: str = "seg", *, tb: str = "1/15360", width: int = 1920,
         streams: int = 2, v_codec: str = "h264", a_codec: str = "aac",
         v_dur: int = 9000, a_dur: int = 9000) -> dict:
    return {
        "name": name,
        "stream_count": streams,
        "container_ms": max(v_dur, a_dur),
        "video": {"codec": v_codec, "width": width, "height": 1080,
                  "pix_fmt": "yuv420p", "profile": "High", "level": 42,
                  "fps": 60.0, "time_base": tb, "duration_ms": v_dur},
        "audio": None if a_codec is None else {
            "codec": a_codec, "sample_rate": 48000, "channels": 2,
            "duration_ms": a_dur},
    }


class SegmentCheckTests(unittest.TestCase):
    def test_accepts_matching_segments(self) -> None:
        self.assertEqual(ca.check_segments([spec("a"), spec("b")], CFG), [])

    def test_rejects_mixed_video_time_base(self) -> None:
        problems = ca.check_segments([spec("a"), spec("b", tb="1/19001")], CFG)
        self.assertTrue(any("mixed video time base" in p for p in problems), problems)

    def test_rejects_wrong_resolution(self) -> None:
        problems = ca.check_segments([spec(width=1280)], CFG)
        self.assertTrue(any("1280x1080" in p for p in problems), problems)

    def test_rejects_extra_streams(self) -> None:
        problems = ca.check_segments([spec(streams=3)], CFG)
        self.assertTrue(any("3 streams" in p for p in problems), problems)

    def test_rejects_audio_mismatch(self) -> None:
        problems = ca.check_segments([spec(a_codec="opus")], CFG)
        self.assertTrue(any("audio codec opus" in p for p in problems), problems)

    def test_rejects_av_drift(self) -> None:
        problems = ca.check_segments([spec(v_dur=9000, a_dur=9300)], CFG)
        self.assertTrue(any("A/V duration delta" in p for p in problems), problems)


class ConcatListTests(unittest.TestCase):
    def test_writes_forward_slash_quoted_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            a = base / "clip one.mp4"
            b = base / "片头.mp4"
            a.write_bytes(b"")
            b.write_bytes(b"")
            out = ca.write_concat_list([a, b], base / "list.txt")
            text = out.read_text(encoding="utf-8")
            self.assertIn(f"file '{a.as_posix()}'", text)
            self.assertIn(f"file '{b.as_posix()}'", text)
            self.assertEqual(len(text.strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
