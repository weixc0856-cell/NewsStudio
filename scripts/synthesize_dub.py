"""Synthesize Chinese dub segments through the isolated CosyVoice microservice.

The main project never imports CosyVoice: this script only speaks HTTP to
http://127.0.0.1:50000 (see D:\\AI\\CosyVoice-Runtime).

Contract (docs/配音方案.md):
    input : structured dub script JSON -- one short sentence per entry
            [{"sentence_id": 1, "target_start_sec": 0.0,
              "max_duration_sec": 4.5, "text": "..."}]
    output: one WAV per sentence + optional timeline track + manifest.json
            every sentence is duration-checked with ffprobe; sentences over
            budget are lightly sped up with atempo (1.05x ~ 1.12x).

Usage:
    uv run python scripts/synthesize_dub.py --script dub/<id>/dub_script.json
    uv run python scripts/synthesize_dub.py --script ... --build-track
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS: dict[str, Any] = {
    "base_url": "http://127.0.0.1:50000",
    "prompt_wav": r"D:\AI\CosyVoice-Runtime\assets\my_voice_5s.wav",
    "prompt_text": "",
    "speaker": "",              # SFT preset speaker id (e.g. 中文男); overrides prompt_wav
    "min_tempo": 1.05,
    "max_tempo": 1.12,
    "tolerance_s": 0.05,
    "tts_timeout_s": 900,
    "wait_s": 180,
    "max_chars": 60,
}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (ROOT / p)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def run_cmd(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def probe_duration(path: Path) -> float:
    proc = run_cmd([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=duration", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ], timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {proc.stderr.strip()[-300:]}")
    data = json.loads(proc.stdout or "{}")
    for key in ("streams", "format"):
        for item in data.get(key, []) if isinstance(data.get(key), list) else [data.get(key, {})]:
            value = (item or {}).get("duration")
            if value:
                return float(value)
    raise RuntimeError(f"no duration in ffprobe output for {path}")


def apply_tempo(src: Path, dst: Path, factor: float) -> None:
    proc = run_cmd([
        "ffmpeg", "-hide_banner", "-y", "-i", str(src),
        "-filter:a", f"atempo={factor:.4f}", "-c:a", "pcm_s16le", str(dst),
    ], timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"atempo failed: {proc.stderr.strip()[-300:]}")


def wait_for_service(base: str, wait_s: int) -> dict[str, Any]:
    deadline = time.time() + wait_s
    last = ""
    while time.time() < deadline:
        try:
            resp = requests.get(f"{base}/health", timeout=5)
            info = resp.json()
            status = info.get("status")
            if status == "ready":
                return info
            if status == "error":
                raise RuntimeError(f"CosyVoice failed to load: {info.get('error')}")
            last = f"status={status}"
        except requests.RequestException as exc:
            last = str(exc)
        time.sleep(3)
    raise RuntimeError(f"CosyVoice service not ready at {base} after {wait_s}s ({last})")


def load_script(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("sentences") or data.get("items") or data.get("dub_script")
    if not isinstance(data, list) or not data:
        raise ValueError("dub script must be a non-empty JSON array of sentences")
    sentences: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            raise ValueError(f"sentence {index} has empty text")
        sentences.append({
            "sentence_id": int(item.get("sentence_id", index)),
            "target_start_sec": float(item.get("target_start_sec", 0.0)),
            "max_duration_sec": float(item.get("max_duration_sec", 0.0)),
            "text": text,
        })
    return sentences


YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)\s*年?")
DIGITS_ZH = "零一二三四五六七八九"


def normalize_for_tts(text: str) -> str:
    """Read years digit-by-digit before CosyVoice's text frontend.

    The bundled TN reads ``2026`` as a cardinal (两千零二十六); a year must be
    spoken 二零二六.  Only 4-digit years 1900-2099 are rewritten, and an
    existing 年 (with optional space) is absorbed so it is not duplicated.
    """
    def _year(match: re.Match[str]) -> str:
        return "".join(DIGITS_ZH[int(digit)] for digit in match.group(1)) + "年"
    return YEAR_RE.sub(_year, text)


SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")


def split_spoken_sentences(text: str) -> list[str]:
    """Split 5W1H copy on sentence-final punctuation / newlines, keeping the mark."""
    return [part.strip() for part in SENTENCE_RE.findall(text) if part.strip()]


def write_silence_wav(path: Path, ms: int, sample_rate: int = 24000) -> None:
    """Deterministic digital silence (-inf dB) as PCM16 mono."""
    proc = run_cmd([
        "ffmpeg", "-hide_banner", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r={int(sample_rate)}:cl=mono",
        "-t", f"{int(ms) / 1000:.3f}", "-c:a", "pcm_s16le", str(path),
    ], timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"silence generation failed: {proc.stderr.strip()[-300:]}")


def concat_wavs(parts: list[Path], out: Path) -> None:
    """Concatenate same-format PCM WAVs without re-encoding the samples."""
    listing = out.with_suffix(".concat.txt")
    listing.write_text(
        "".join(f"file '{part.resolve().as_posix()}'" + chr(10) for part in parts),
        encoding="utf-8")
    proc = run_cmd([
        "ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0",
        "-i", str(listing), "-c:a", "pcm_s16le", str(out),
    ], timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"wav concat failed: {proc.stderr.strip()[-400:]}")


def tts_request(base: str, text: str, prompt_wav: str | None, prompt_text: str | None,
                timeout: int, speaker: str | None = None) -> bytes:
    payload: dict[str, Any] = {"text": normalize_for_tts(text), "speed": 1.0,
                               "text_frontend": True}
    if speaker:
        payload["speaker"] = speaker
    if prompt_wav:
        payload["prompt_wav"] = prompt_wav
    if prompt_text:
        payload["prompt_text"] = prompt_text
    resp = requests.post(f"{base}/tts", json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"TTS {resp.status_code}: {resp.text[:400]}")
    return resp.content


def build_track(items: list[dict[str, Any]], out_path: Path, sample_rate: str = "24000") -> Path:
    """Place every final WAV at its target_start_sec and mix into one timeline."""
    usable = [i for i in items if i.get("final_path")]
    if not usable:
        raise RuntimeError("no synthesized audio to build a track from")
    total = max(i["target_start_sec"] + i["final_seconds"] for i in usable) + 0.5
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for item in usable:
        cmd += ["-i", str(resolve(item["final_path"]))]
    parts = []
    for index, item in enumerate(usable):
        delay_ms = int(round(item["target_start_sec"] * 1000))
        parts.append(f"[{index}:a]aresample={sample_rate},adelay={delay_ms}|{delay_ms}[a{index}]")
    labels = "".join(f"[a{index}]" for index in range(len(usable)))
    if len(usable) == 1:
        parts.append(f"{labels}apad=whole_dur={total:.3f}[out]")
    else:
        parts.append(f"{labels}amix=inputs={len(usable)}:duration=longest:normalize=0,"
                     f"apad=whole_dur={total:.3f}[out]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[out]",
            "-c:a", "pcm_s16le", "-ar", sample_rate, "-ac", "1", str(out_path)]
    proc = run_cmd(cmd, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"track build failed: {proc.stderr.strip()[-400:]}")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="CosyVoice dub synthesis (HTTP client)")
    ap.add_argument("--script", required=True, help="structured dub script JSON")
    ap.add_argument("--out-dir", default=None, help="default: dub/<script-stem>/")
    ap.add_argument("--base", default=DEFAULTS["base_url"])
    ap.add_argument("--prompt-wav", default=DEFAULTS["prompt_wav"])
    ap.add_argument("--prompt-text", default=DEFAULTS["prompt_text"])
    ap.add_argument("--speaker", default=DEFAULTS["speaker"],
                    help="SFT preset speaker id (e.g. 中文男); skips prompt_wav when set")
    ap.add_argument("--min-tempo", type=float, default=DEFAULTS["min_tempo"])
    ap.add_argument("--max-tempo", type=float, default=DEFAULTS["max_tempo"])
    ap.add_argument("--tolerance", type=float, default=DEFAULTS["tolerance_s"],
                    help="allowed overshoot in seconds after atempo (encoder padding noise)")
    ap.add_argument("--timeout", type=int, default=DEFAULTS["tts_timeout_s"])
    ap.add_argument("--wait", type=int, default=DEFAULTS["wait_s"])
    ap.add_argument("--max-chars", type=int, default=DEFAULTS["max_chars"])
    ap.add_argument("--no-track", action="store_true", help="skip timeline track build")
    ap.add_argument("--allow-over", action="store_true",
                    help="keep going when a sentence still exceeds budget after max tempo")
    args = ap.parse_args()

    script_path = resolve(args.script)
    if not script_path.exists():
        log(f"script not found: {script_path}")
        return 2
    sentences = load_script(script_path)

    out_dir = resolve(args.out_dir) if args.out_dir else ROOT / "dub" / script_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"waiting for CosyVoice at {args.base} ...")
    health = wait_for_service(args.base, args.wait)
    log(f"service ready: model={health.get('model_class')} device={health.get('device')} "
        f"sample_rate={health.get('sample_rate')}")

    speaker = (args.speaker or "").strip()
    prompt_wav = str(resolve(args.prompt_wav)) if args.prompt_wav and not speaker else ""
    prompt_text = args.prompt_text or None

    items: list[dict[str, Any]] = []
    over_budget = 0
    for sentence in sentences:
        sid = sentence["sentence_id"]
        text = sentence["text"]
        budget = sentence["max_duration_sec"]
        if len(text) > args.max_chars:
            log(f"warning: sentence {sid} has {len(text)} chars > {args.max_chars}; "
                "long lines hurt pacing and cloning quality")

        raw_path = out_dir / f"sentence-{sid:02d}.raw.wav"
        final_path = out_dir / f"sentence-{sid:02d}.wav"

        started = time.time()
        audio = tts_request(args.base, text, prompt_wav, prompt_text, args.timeout,
                            speaker=speaker or None)
        raw_path.write_bytes(audio)
        synth_s = time.time() - started
        raw_s = probe_duration(raw_path)

        tempo = 1.0
        final_s = raw_s
        status = "OK"
        if budget > 0 and raw_s > budget:
            needed = raw_s / budget
            tempo = min(max(needed, args.min_tempo), args.max_tempo)
            apply_tempo(raw_path, final_path, tempo)
            final_s = probe_duration(final_path)
            if final_s <= budget + args.tolerance:
                status = "FIT"
            else:
                status = "OVER"
                over_budget += 1
        else:
            shutil.copyfile(raw_path, final_path)

        items.append({
            "sentence_id": sid,
            "text": text,
            "target_start_sec": sentence["target_start_sec"],
            "max_duration_sec": budget,
            "raw_path": rel(raw_path),
            "raw_seconds": round(raw_s, 3),
            "tempo": round(tempo, 4),
            "final_path": rel(final_path),
            "final_seconds": round(final_s, 3),
            "status": status,
            "synth_seconds": round(synth_s, 2),
            "rtf": round(synth_s / max(raw_s, 1e-6), 2),
        })
        log(f"[{sid:02d}] {status:4s} raw={raw_s:5.2f}s final={final_s:5.2f}s "
            f"budget={budget:5.2f}s tempo={tempo:4.2f} rtf={synth_s / max(raw_s, 1e-6):4.2f} "
            f"| {text[:28]}")

    track_path: Path | None = None
    if not args.no_track:
        track_path = build_track(items, out_dir / "track.wav", str(health.get("sample_rate") or 24000))
        log(f"track built: {rel(track_path)} ({probe_duration(track_path):.2f}s)")

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "script": rel(script_path),
        "base_url": args.base,
        "prompt_wav": rel(Path(prompt_wav)) if prompt_wav else "",
        "speaker": speaker,
        "service": {k: health.get(k) for k in ("model_class", "model_dir", "device",
                                               "sample_rate", "text_frontend")},
        "over_budget": over_budget,
        "tolerance_s": args.tolerance,
        "track": rel(track_path) if track_path else None,
        "items": items,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    log("---- duration check ----")
    for item in items:
        log(f"  #{item['sentence_id']:02d} target={item['target_start_sec']:6.2f}s "
            f"budget={item['max_duration_sec']:5.2f}s final={item['final_seconds']:5.2f}s "
            f"tempo={item['tempo']:.2f} {item['status']}")
    log(f"manifest: {rel(manifest_path)}")

    if over_budget and not args.allow_over:
        log(f"{over_budget} sentence(s) still over budget after {args.max_tempo}x; "
            "shorten the text or pass --allow-over")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
