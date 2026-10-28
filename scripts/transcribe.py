"""Transcribe a downloaded video locally with faster-whisper.

Used as a fallback when YouTube's caption endpoint is rate-limited (HTTP 429).
Produces subtitles/<video-id>.en.srt, which build_subs.py consumes.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB_DIR = ROOT / "subtitles"
sys.path.insert(0, str(ROOT / "scripts"))

from build_subs import words_to_sentences  # noqa: E402


def fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def extract_audio(video: Path, wav: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn",
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", help="input video (defaults to the newest file in downloads/)")
    ap.add_argument("--model", default="medium.en")
    ap.add_argument("--language", default="en")
    ap.add_argument("--threads", type=int, default=min(16, os.cpu_count() or 8))
    args = ap.parse_args()

    video = Path(args.video) if args.video else max(
        (ROOT / "downloads").glob("*.mkv"), key=lambda p: p.stat().st_mtime
    )
    video_id = video.stem.rsplit("[", 1)[-1].rstrip("]")
    SUB_DIR.mkdir(exist_ok=True)

    wav = SUB_DIR / f"{video_id}.probe.wav"
    print(f"extracting audio: {video.name}", flush=True)
    extract_audio(video, wav)
    print(f"audio: {wav.stat().st_size / 1e6:.1f} MB", flush=True)

    import wave

    import numpy as np

    with wave.open(str(wav), "rb") as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    audio = audio.astype(np.float32) / 32768.0

    from faster_whisper import WhisperModel

    print(f"loading model {args.model} (int8, {args.threads} threads)", flush=True)
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=args.threads)
    segments, info = model.transcribe(
        audio,
        language=args.language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=True,
        condition_on_previous_text=False,
    )
    print(f"duration: {info.duration:.1f}s, prob {info.language_probability:.2f}", flush=True)

    words: list[tuple[float, float, str]] = []
    for seg in segments:
        for w in seg.words or []:
            token = w.word.strip()
            if token:
                words.append((w.start, w.end, token))
        print(f"[{seg.end:7.1f}s] {seg.text.strip()}", flush=True)

    cues = words_to_sentences(words)
    out = SUB_DIR / f"{video_id}.{args.language}.srt"
    blocks = [
        f"{i}\n{fmt_srt(s)} --> {fmt_srt(e)}\n{text}\n"
        for i, (s, e, text) in enumerate(cues, 1)
    ]
    out.write_text("\n".join(blocks), encoding="utf-8")
    print(f"wrote {out} ({len(cues)} cues from {len(words)} words)", flush=True)

    wav.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
