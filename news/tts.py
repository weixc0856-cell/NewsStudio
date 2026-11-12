"""VoxCPM2 (50000) client and per-segment narration runner.

Service contract: POST /tts with {text, prompt_wav, prompt_text, speed} returns
audio/wav.  The runtime is CPU-only and RTF is roughly 9-12x, so a 12-minute
episode can take 1.5-2.5 hours.  Run it in the background and do not start a
second TTS instance.

Start it with the VoxCPM runtime launcher (``$VOXCPM_RUNTIME``, see .env);
stop it afterwards.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:50000"
DEFAULT_PROMPT_WAV = os.environ.get("NEWS_TTS_PROMPT_WAV", "")
DEFAULT_PROMPT_TEXT = "Welcome to this lesson. Today, we will look at how the model works."


def health(base_url: str = DEFAULT_BASE_URL, timeout: float = 5.0) -> dict[str, Any]:
    response = requests.get(f"{base_url.rstrip('/')}/health", timeout=timeout)
    response.raise_for_status()
    return response.json()


def is_ready(base_url: str = DEFAULT_BASE_URL) -> bool:
    try:
        return health(base_url).get("status") in ("ready", "ok")
    except requests.RequestException:
        return False


def synthesize(*, text: str, out: str | Path, prompt_wav: str | Path | None = None,
               prompt_text: str | None = None, speed: float = 1.0,
               base_url: str = DEFAULT_BASE_URL, timeout_s: float = 900) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("text is empty")
    prompt_raw = prompt_wav or os.environ.get("NEWS_TTS_PROMPT_WAV") or DEFAULT_PROMPT_WAV
    if not prompt_raw:
        raise FileNotFoundError(
            "English reference voice not configured: set NEWS_TTS_PROMPT_WAV in .env")
    prompt = Path(prompt_raw)
    if not prompt.is_file():
        raise FileNotFoundError(f"English reference voice not found: {prompt}")
    payload = {
        "text": text,
        "prompt_wav": str(prompt),
        "prompt_text": prompt_text or os.environ.get("NEWS_TTS_PROMPT_TEXT") or DEFAULT_PROMPT_TEXT,
        "speed": speed,
        "text_frontend": True,
    }
    response = requests.post(f"{base_url.rstrip('/')}/tts", json=payload, timeout=timeout_s)
    response.raise_for_status()
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return {
        "text": text,
        "wav": str(path),
        "audio_seconds": float(response.headers.get("X-Audio-Seconds", 0) or 0),
        "synth_seconds": float(response.headers.get("X-Synth-Seconds", 0) or 0),
        "sample_rate": int(response.headers.get("X-Sample-Rate", 48000) or 48000),
        "prompt_mode": response.headers.get("X-Prompt-Mode", ""),
        "speed_stretch": response.headers.get("X-Speed-Stretch", ""),
    }


def narrate_plan(plan_path: str | Path, *, force: bool = False, speed: float = 1.0,
                 prompt_wav: str | None = None, prompt_text: str | None = None,
                 base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    """Synthesize every segment with English narration and update the plan."""
    from .schemas import load_json, write_json

    plan_file = Path(plan_path)
    plan = load_json(plan_file)
    base = plan_file.parent
    voice_dir = base / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    if not is_ready(base_url):
        raise RuntimeError(
            f"VoxCPM is not ready at {base_url}. Start the runtime in "
            f"{os.environ.get('VOXCPM_RUNTIME') or '<VOXCPM_RUNTIME>'} and wait ~30 s; "
            "stop it when the run finishes."
        )
    manifest: list[dict[str, Any]] = []
    for segment in plan.get("segments", []):
        text = (segment.get("narration_text_en") or "").strip()
        if not text:
            continue
        seg_id = segment.get("id") or "segment"
        rel = f"voice/{seg_id}.wav"
        out = base / rel
        if out.is_file() and not force and out.stat().st_size > 0:
            manifest.append({"id": seg_id, "wav": rel, "cached": True})
            segment["narration_wav"] = rel
            continue
        result = synthesize(text=text, out=out, prompt_wav=prompt_wav,
                            prompt_text=prompt_text, speed=speed, base_url=base_url)
        result["id"] = seg_id
        result["wav"] = rel
        manifest.append(result)
        segment["narration_wav"] = rel
    plan["status"] = "narrated"
    write_json(plan_file, plan)
    write_json(voice_dir / "manifest.json", {"episode_id": plan.get("episode_id"),
                                              "segments": manifest})
    return {"episode_id": plan.get("episode_id"), "segments": manifest}
