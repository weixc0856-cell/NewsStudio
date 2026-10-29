"""Generate a local-only 6.0-9.5 s intro: Qwen 5W1H copy + fixed template + CosyVoice.

Design constraints (see docs/片头语与工程化导读规范.md):

* copy    -- the local Qwen (llama-server, 127.0.0.1:8080) writes three
  sentences in a strict Who+Where+When / What+Why/How / We-did structure,
  plus a screen title and a source subtitle. No cloud model, no video model.
* picture -- assets/templates/intro.html is a fixed Swiss/industrial template
  (1920x1080, #0b0e13, 4 px #ff5500 rail, monospace chrome, left alignment).
  Python only substitutes {{PLACEHOLDERS}}. Two deterministic states
  (0 = rail collapsed + title 15 px lower/transparent, 1 = final) are
  screenshotted by local headless Chrome/Edge and crossfaded by FFmpeg.
  The rail is drawn top-to-bottom with drawbox; the frame then holds with a
  0.05 %/s Ken Burns push. No Playwright, Remotion, moviepy or new library.
* voice   -- HTTP to the isolated CosyVoice runtime on 127.0.0.1:50000 with the
  fixed cloned reference voice. atempo is used only inside a 1.15x cap.
* compose -- FFmpeg/QSV, 30 fps, hard 6.0-9.5 s window, audio padded/trimmed
  to the picture length, -shortest, h264 + aac.

Everything is timed in integer milliseconds. The card is verified with ffprobe
and only published to clips/<id>/intro/intro.mp4 when every check passes.

Usage:
    uv run python scripts/generate_intro.py --video-id c88l8daXiv4 `
        --title "CPU 成为新瓶颈：2026 年的数据中心" `
        --summary "AI 推理把 CPU 推成瓶颈……" `
        --series "AI 基建 / 第 21 期" --speaker "DYLAN PATEL / SEMIANALYSIS" `
        --source "SemiAnalysis × Daytona" --stamp "FIELD RECORD / 2026" `
        --stamp-right "2026 / DATACENTER · CPU" --index 021
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dub_mix  # noqa: E402
import synthesize_dub as sd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 2
TEMPLATE_DIR = ROOT / "assets" / "templates"
INTRO_TEMPLATE = "intro.html"            # McKinsey poster (production)
CLASSIC_TEMPLATE = "intro-classic.html"  # previous industrial template (kept for fallback)
CARD_TEMPLATE = "transition.html"

DEFAULTS: dict[str, Any] = {
    "width": 1920,
    "height": 1080,
    "fps": 60,                  # CFR 60: same rate as the highlight clips / reel
    "av_tolerance_ms": 60,      # max |video - audio| duration in the intro
    "lead_ms": 200,             # picture starts, voice starts 200 ms later
    "voice_head_silence_ms": 600,  # silence baked into narration.wav; lead becomes 0
    "tail_ms": 250,             # hold the final frame after the voice
    "min_tail_ms": 100,
    "min_duration_ms": 10_000,
    "max_duration_ms": 20_000,
    "duration_guard_ms": 60,    # encoder/packet padding: plan stops this far below the cap
    "voice_budget_ms": 16_000,  # atempo target; 12-18 s intros rarely need it
    "max_tempo": 1.15,
    "tolerance_ms": 250,
    "base_url": "http://127.0.0.1:50000",
    "prompt_wav": sd.DEFAULTS["prompt_wav"],
    "voice_speaker": "中文女",   # SFT preset speaker id; when set, prompt_wav is not sent
    "tts_timeout_s": sd.DEFAULTS["tts_timeout_s"],
    "wait_s": sd.DEFAULTS["wait_s"],
    "dub_target_db": dub_mix.DEFAULTS["dub_target_db"],
    "qsv_quality": 19,
    "audio_bitrate": "160k",
    "audio_sample_rate": 48000,
    "browser_timeout_s": 90,
    # copy: local Qwen (llama-server)
    "llm_base": "http://127.0.0.1:8080",
    "llm_model": None,
    "llm_timeout_s": 300,
    "llm_retries": 2,
    "llm_temperature": 0.2,
    "copy_min_chars": 60,       # spoken units: CJK chars + latin word tokens
    "copy_max_chars": 95,
    "copy_min_title": 12,
    "copy_max_title": 24,
    "copy_min_subtitle": 10,
    "copy_max_subtitle": 48,
    # deterministic motion
    "bar_reveal_ms": 550,
    "title_delay_ms": 150,
    "title_fade_ms": 550,
    "fade_in_ms": 200,
    "fade_out_ms": 400,
    "ken_burns_per_sec": 0.0005,   # 0.05 %/s
    "accent": "#ff5500",
}

FORBIDDEN_WORDS = (
    "震撼", "颠覆", "杀疯", "炸裂", "王炸", "封神", "史诗", "狂欢", "重磅", "炸场",
    "逆天", "天花板", "降维打击", "彻底", "疯狂", "爆款", "必看", "速看", "太强", "无敌",
    # 2026-10-29: 书面/营销腔，女声口语化解说里读出来很假
    "拆解", "实录", "关键观点解析", "深度解读", "全面分析", "工业级",
)

_CJK_RE = re.compile("[" + chr(0x4E00) + "-" + chr(0x9FFF) + "]")
_LATIN_RE = re.compile(r"[A-Za-z]+")
_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_CLOSING_RE = re.compile(r"(原声|来听|听听)")

BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)

FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (ROOT / p)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_cmd(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=str(ROOT))


def filter_path(path: Path) -> str:
    text = path.resolve().as_posix()
    for ch in "':,[];":
        text = text.replace(ch, "\\" + ch)
    return text


# --------------------------------------------------------------------------
# copy: local Qwen, 5W1H engineering brief
# --------------------------------------------------------------------------
COPY_SYSTEM = (
    "你是一名科技纪录片片头撰稿人，风格冷峻、克制、可核查。"
    "你只输出一个严格合法的 JSON 对象，不输出解释、不输出 Markdown 代码块。"
)


def build_copy_prompt(title: str, summary: str) -> str:
    nl = chr(10)
    lines = [
        f"本期节目：{title}",
        f"内容摘要：{summary}",
        "",
        "请写一段 12–18 秒的中文播客片头导读，由女声念出。严格输出 JSON：",
        '{"intro_spoken_text": "...", "screen_title": "...", "screen_subtitle": "..."}',
        "",
        "规则：",
        "1. 把 5W1H 说清楚：谁、在哪、何时、讲了什么、为什么值得听。"
        "拆成 5–6 个短句，每句不超过 14 个字（英文单词各算 1 个字），"
        "整段 60–95 个字。",
        "2. 像真人主持在说话，不要新闻稿腔、不要 PPT 标题腔；"
        "可以用“来听、听听、为什么、怎么说、现场”。",
        "3. 禁止使用：拆解、实录、关键观点解析、深度解读、全面分析、工业级，以及震撼、颠覆、"
        "杀疯、炸裂、王炸、封神、史诗、狂欢、重磅、炸场、逆天、天花板、降维打击、彻底、疯狂、"
        "爆款、必看、速看、太强、无敌。",
        "4. 年份必须写成“二零二六年”，不要写阿拉伯数字。",
        "5. Daytona、Dylan Patel、CPU、AI 等专有名词保留英文，前后用标点隔开，留出停顿。",
        "6. 最后一句必须是引导听原声的短句，例如“来听原声。”",
        "7. screen_title：12–18 个汉字（不含空格）；screen_subtitle：15–25 个汉字。",
        "8. 只输出 JSON，不要代码块。",
        "",
        "正例（照这个节奏写）：",
        '{"intro_spoken_text":"二零二六年，Daytona 现场。'
        'Dylan Patel 说，CPU 为什么总不够用？'
        '推理模型把训练和验证闭环压紧。GPU 的闲置率反而一路上涨。'
        '算力到底卡在哪一步？听听他怎么说，来听原声。",'
        '"screen_title":"CPU 为何成为 AI 新瓶颈",'
        '"screen_subtitle":"Dylan Patel · SemiAnalysis，2026"}',
        "反例（太长、太书面，禁止）：这是 Dylan Patel 在 2026 年 Daytona 大会的一手公开实录。"
        "面对 AI 推理带来的 CPU 短缺，他详拆了智能体训练与验证的真实算力边界。"
        "我们整理了完整推演并配齐中英双语，来看现场原声。",
    ]
    return nl.join(lines)


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise ValueError("no JSON object in response")
        obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("response JSON is not an object")
    return obj


def _count_sentences(text: str) -> int:
    return sum(1 for ch in text if ch in "。！？!?")


def _spoken_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？!?])", text) if part.strip()]


def _spoken_units(text: str) -> int:
    """CJK characters + latin word tokens; punctuation and digits are ignored."""
    return len(_CJK_RE.findall(text)) + len(_LATIN_RE.findall(text))


def _validate_spoken_text(text: str, cfg: dict[str, Any]) -> str:
    text = " ".join(text.split())
    sentences = _spoken_sentences(text)
    if not 5 <= len(sentences) <= 6:
        raise ValueError(f"spoken text must be 5-6 sentences, got {len(sentences)}")
    units = _spoken_units(text)
    lo, hi = int(cfg["copy_min_chars"]), int(cfg["copy_max_chars"])
    if not lo <= units <= hi:
        raise ValueError(f"spoken text is {units} units, cap [{lo}, {hi}]")
    for sentence in sentences:
        if _spoken_units(sentence) > 14:
            raise ValueError(f"sentence is {_spoken_units(sentence)} units (>14): {sentence}")
    if _YEAR_RE.search(text):
        raise ValueError("year must be written as 二零二六年, not digits")
    if not _CLOSING_RE.search(sentences[-1]):
        raise ValueError("last sentence must invite listening to the original audio")
    for word in FORBIDDEN_WORDS:
        if word in text:
            raise ValueError(f"forbidden word: {word}")
    return text


def _plain_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def normalize_copy(obj: dict[str, Any], cfg: dict[str, Any] | None = None) -> dict[str, str]:
    cfg = {**DEFAULTS, **(cfg or {})}
    spoken = " ".join(str(obj.get("intro_spoken_text", "")).split())
    screen_title = " ".join(str(obj.get("screen_title", "")).split())
    screen_subtitle = " ".join(str(obj.get("screen_subtitle", "")).split())
    if not spoken or not screen_title or not screen_subtitle:
        raise ValueError("copy is missing intro_spoken_text/screen_title/screen_subtitle")
    spoken = _validate_spoken_text(spoken, cfg)
    title_len = _plain_len(screen_title)
    if not (int(cfg["copy_min_title"]) <= title_len <= int(cfg["copy_max_title"])):
        raise ValueError(f"screen_title is {title_len} chars, cap "
                         f"[{cfg['copy_min_title']}, {cfg['copy_max_title']}]")
    subtitle_len = _plain_len(screen_subtitle)
    if not (int(cfg["copy_min_subtitle"]) <= subtitle_len <= int(cfg["copy_max_subtitle"])):
        raise ValueError(f"screen_subtitle is {subtitle_len} chars, cap "
                         f"[{cfg['copy_min_subtitle']}, {cfg['copy_max_subtitle']}]")
    for word in FORBIDDEN_WORDS:
        if word in spoken or word in screen_title or word in screen_subtitle:
            raise ValueError(f"forbidden hype word: {word}")
    return {
        "intro_spoken_text": spoken,
        "screen_title": screen_title,
        "screen_subtitle": screen_subtitle,
    }


def _llm_headers(cfg: dict[str, Any]) -> dict[str, str]:
    key = str(cfg.get("llm_api_key") or os.environ.get("LLM_API_KEY") or "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def generate_copy_llm(*, title: str, summary: str,
                      cfg: dict[str, Any]) -> dict[str, Any]:
    """Ask the local llama-server for the 5W1H copy. Local HTTP only."""
    base = str(cfg["llm_base"]).rstrip("/")
    headers = _llm_headers(cfg)
    model = cfg.get("llm_model")
    if not model:
        resp = requests.get(f"{base}/v1/models", timeout=30, headers=headers)
        resp.raise_for_status()
        model = resp.json()["data"][0]["id"]
    prompt = build_copy_prompt(title, summary)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": COPY_SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": float(cfg["llm_temperature"]),
        "max_tokens": 500,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, int(cfg["llm_retries"]) + 2):
        record: dict[str, Any] = {"attempt": attempt}
        try:
            if attempt > 1:
                payload["messages"][1]["content"] = (
                    prompt + "\n\n注意：上次不合格。必须写够 60–95 个字（英文单词各算 1 个字），"
                    "5–6 句，每句 10–14 个字，口语化，年份写二零二六年，"
                    "最后一句必须引导听原声；screen_title 至少 12 个汉字（不含空格）。"
                )
            resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                 timeout=(10, int(cfg["llm_timeout_s"])), headers=headers)
            if resp.status_code == 400 and "response_format" in payload:
                payload.pop("response_format")
                resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                     timeout=(10, int(cfg["llm_timeout_s"])), headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            record["raw"] = content
            copy = normalize_copy(_extract_json_object(content), cfg)
            record["ok"] = True
            attempts.append(record)
            log(f"copy from Qwen: {copy['screen_title']} | "
                f"{copy['intro_spoken_text']}")
            return {"source": "llm", "model": model, "base_url": base,
                    "prompt": prompt, **copy, "attempts": attempts}
        except Exception as exc:
            record["ok"] = False
            record["error"] = str(exc)
            attempts.append(record)
            log(f"copy attempt {attempt} failed: {exc}")
            if attempt <= int(cfg["llm_retries"]):
                time.sleep(1)
    raise RuntimeError(f"Qwen copy failed after {len(attempts)} attempts: "
                       f"{attempts[-1].get('error')}")


COMPRESS_SYSTEM = "你只输出严格合法的 JSON，不输出解释或 Markdown。"


def build_compress_prompt(spoken: str) -> str:
    lines = [
        "下面的片头导读朗读时间过长。请压缩到 60–95 个字（英文单词各算 1 个字），"
        "保持 5–6 个短句、每句不超过 14 个字；语气仍要像真人在说话，"
        "最后一句仍要引导听原声；不要新增事实。",
        "正例：二零二六年，Daytona 现场，AI 算力的账。Dylan Patel 说，CPU 为什么总不够用？"
        "听听他怎么说，算力到底卡在哪？来听原声。",
        f"原文：{spoken}",
        '只输出 JSON：{"intro_spoken_text":"..."}',
    ]
    return chr(10).join(lines)


def _validate_spoken(text: str, cfg: dict[str, Any]) -> str:
    return _validate_spoken_text(text, cfg)


def rewrite_copy_llm(*, spoken: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Ask Qwen to compress the spoken line when TTS runs past the window."""
    base = str(cfg["llm_base"]).rstrip("/")
    headers = _llm_headers(cfg)
    model = cfg.get("llm_model")
    if not model:
        resp = requests.get(f"{base}/v1/models", timeout=30, headers=headers)
        resp.raise_for_status()
        model = resp.json()["data"][0]["id"]
    prompt = build_compress_prompt(spoken)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": COMPRESS_SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": float(cfg["llm_temperature"]),
        "max_tokens": 250,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, int(cfg["llm_retries"]) + 2):
        record: dict[str, Any] = {"attempt": attempt}
        if attempt > 1:
            payload["messages"][1]["content"] = (
                prompt + "\n\n注意：上次仍过长。必须压到 35–48 个字"
                         "（英文单词各算 1 个字），保持 5–6 个短句、每句不超过 14 个字，最后一句仍要引导听原声，直接输出 JSON。"
            )
        try:
            resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                 timeout=(10, int(cfg["llm_timeout_s"])), headers=headers)
            if resp.status_code == 400 and "response_format" in payload:
                payload.pop("response_format")
                resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                     timeout=(10, int(cfg["llm_timeout_s"])), headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            record["raw"] = content
            text = _validate_spoken(
                str(_extract_json_object(content).get("intro_spoken_text", "")), cfg)
            record["ok"] = True
            attempts.append(record)
            log(f"Qwen compressed the spoken line to {_plain_len(text)} chars")
            return {"text": text, "prompt": prompt, "attempts": attempts}
        except Exception as exc:
            record["ok"] = False
            record["error"] = str(exc)
            attempts.append(record)
            log(f"compress attempt {attempt} failed: {exc}")
            if attempt <= int(cfg["llm_retries"]):
                time.sleep(1)
    raise RuntimeError(f"Qwen compress failed after {len(attempts)} attempts: "
                       f"{attempts[-1].get('error')}")


# --------------------------------------------------------------------------
# timing
# --------------------------------------------------------------------------
def plan_timeline(voice_ms: int, cfg: dict[str, Any] | None = None) -> dict[str, int]:
    """Place the voice inside the hard 6.0-9.5 s window."""
    cfg = {**DEFAULTS, **(cfg or {})}
    if voice_ms <= 0:
        raise ValueError("voice duration must be positive")
    lead = int(cfg["lead_ms"])
    tail = int(cfg["tail_ms"])
    min_tail = int(cfg["min_tail_ms"])
    min_dur = int(cfg["min_duration_ms"])
    max_dur = int(cfg["max_duration_ms"])
    guard = int(cfg.get("duration_guard_ms", 0))
    # The encoder appends AAC/frame padding (measured +21 ms).  Plan below the
    # hard cap so the finished file can never land outside 6.0-9.5 s.
    plan_cap = max_dur - guard
    duration = lead + voice_ms + tail
    if duration > plan_cap:
        duration = lead + voice_ms + min_tail
    if duration < min_dur:
        duration = min_dur
    if duration > plan_cap:
        raise ValueError(
            f"narration is {voice_ms} ms; lead {lead} + min tail {min_tail} "
            f"exceeds the {plan_cap} ms plan cap (window {max_dur} - {guard} ms "
            f"encoder guard) -- shorten the copy or lower the tempo cap"
        )
    return {
        "duration_ms": duration,
        "lead_ms": lead,
        "voice_ms": voice_ms,
        "tail_ms": duration - lead - voice_ms,
    }


def tempo_for(voice_ms: int, cfg: dict[str, Any] | None = None) -> float:
    cfg = {**DEFAULTS, **(cfg or {})}
    budget = int(cfg["voice_budget_ms"])
    if voice_ms <= budget:
        return 1.0
    return min(voice_ms / budget, float(cfg["max_tempo"]))


def plan_animation(duration_ms: int, tail_ms: int,
                   cfg: dict[str, Any] | None = None) -> dict[str, int | float]:
    cfg = {**DEFAULTS, **(cfg or {})}
    duration = int(duration_ms)
    bar = int(cfg["bar_reveal_ms"])
    delay = int(cfg["title_delay_ms"])
    fade = int(cfg["title_fade_ms"])
    fade_out = min(int(cfg["fade_out_ms"]), max(int(tail_ms), 100))
    if delay + fade >= duration - fade_out:
        fade = max(duration - fade_out - delay - 50, 200)
    return {
        "duration_ms": duration,
        "bar_reveal_ms": bar,
        "title_delay_ms": delay,
        "title_fade_ms": fade,
        "fade_in_ms": int(cfg["fade_in_ms"]),
        "fade_out_ms": fade_out,
        "ken_burns_per_sec": float(cfg["ken_burns_per_sec"]),
    }


# --------------------------------------------------------------------------
# fixed templates
# --------------------------------------------------------------------------
def load_template(name: str) -> str:
    path = TEMPLATE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"template not found: {path}")
    return path.read_text(encoding="utf-8")


def render_template(name: str, values: dict[str, str]) -> str:
    text = load_template(name)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    leftover = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", text)))
    if leftover:
        raise ValueError(f"unfilled placeholders in {name}: {leftover}")
    return text


def build_intro_html(*, copy: dict[str, str], chrome: dict[str, str],
                     state: int) -> str:
    values = {
        "ACCENT": chrome["accent"],
        "STATE": str(state),
        "SERIES": html.escape(chrome["series"]),
        "INDEX": html.escape(chrome["index"]),
        "STAMP": html.escape(chrome["stamp"]),
        "EYEBROW": html.escape(chrome["eyebrow"]),
        "EYEBROW_RIGHT": html.escape(chrome["eyebrow_right"]),
        "TITLE": html.escape(copy["screen_title"]),
        "SUBTITLE": html.escape(copy["screen_subtitle"]),
        "SPEAKER": html.escape(chrome["speaker"]),
        "SOURCE": html.escape(chrome["source"]),
        "STAMP_RIGHT": html.escape(chrome["stamp_right"]),
    }
    return render_template(CLASSIC_TEMPLATE, values)


# --------------------------------------------------------------------------
# McKinsey-style static poster (production intro)
# --------------------------------------------------------------------------
POSTER_DEFAULTS: dict[str, Any] = {
    "width": 1920,
    "height": 1080,
    "fps": 60,
    "min_duration_ms": 4000,
    "short_max_ms": 6000,
    "full_min_ms": 7000,
    "max_duration_ms": 9500,
    "silent_duration_ms": 5000,
    "lead_ms": 200,
    "tail_ms": 250,
    "qsv_quality": 19,
    "audio_bitrate": "160k",
    "audio_sample_rate": 48000,
}


def poster_values(*, title_en: str, title_zh: str, speaker: str, event: str,
                  organization: str, verification: str,
                  summary_zh: str = "", insight_1: str = "",
                  insight_2: str = "", insight_3: str = "",
                  kicker: str = "TECHNICAL HIGHLIGHTS", index: str = "",
                  series: str = "", accent: str = "#ff5500") -> dict[str, str]:
    def esc(value: str) -> str:
        return html.escape(value, quote=False)

    values = {
        "TITLE_EN": esc(title_en.strip()),
        "TITLE_ZH": esc(title_zh.strip()),
        "SUMMARY_ZH": esc(summary_zh.strip() or "—"),
        "INSIGHT_1": esc(insight_1.strip() or "—"),
        "INSIGHT_2": esc(insight_2.strip() or "—"),
        "INSIGHT_3": esc(insight_3.strip() or "—"),
        "SPEAKER": esc(speaker.strip() or "—"),
        "SOURCE_EVENT": esc(event.strip() or "—"),
        "ORGANIZATION": esc(organization.strip() or "—"),
        "VERIFICATION": esc(verification.strip() or "—"),
        "KICKER": esc(kicker.strip() or "TECHNICAL HIGHLIGHTS"),
        "INDEX": esc(index.strip()),
        "SERIES": esc(series.strip()),
        "SERIES_NAME": esc(series.strip()),
        "ACCENT": accent,
    }
    if not values["TITLE_EN"] or not values["TITLE_ZH"]:
        raise ValueError("title-en and title-zh are required")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        raise ValueError("accent must be #RRGGBB")
    return values


def classify_poster_length(duration_ms: int,
                           cfg: dict[str, Any] | None = None) -> str:
    cfg = {**POSTER_DEFAULTS, **(cfg or {})}
    if duration_ms <= int(cfg["short_max_ms"]):
        return "short"
    if duration_ms >= int(cfg["full_min_ms"]):
        return "full"
    return "standard"


def plan_poster_duration(*, silent: bool, voice_ms: int | None = None,
                         requested_ms: int | None = None,
                         cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = {**POSTER_DEFAULTS, **(cfg or {})}
    min_ms, max_ms = int(cfg["min_duration_ms"]), int(cfg["max_duration_ms"])
    if silent:
        duration = int(requested_ms or cfg["silent_duration_ms"])
        if not (min_ms <= duration <= max_ms):
            raise ValueError(f"silent duration {duration} ms outside [{min_ms}, {max_ms}]")
        return {"duration_ms": duration, "mode": classify_poster_length(duration, cfg),
                "voice_ms": 0, "lead_ms": 0, "tail_ms": 0}
    if not voice_ms or voice_ms <= 0:
        raise ValueError("voice mode needs a positive voice duration")
    lead, tail = int(cfg["lead_ms"]), int(cfg["tail_ms"])
    duration = lead + int(voice_ms) + tail
    if duration > max_ms:
        raise ValueError(
            f"voice {voice_ms} ms + lead/tail exceeds the {max_ms} ms hard cap; "
            "shorten the line or apply atempo upstream")
    duration = max(duration, min_ms)
    return {"duration_ms": duration, "mode": classify_poster_length(duration, cfg),
            "voice_ms": int(voice_ms), "lead_ms": lead,
            "tail_ms": duration - lead - voice_ms}


def build_poster_html(*, copy: dict[str, str], chrome: dict[str, str]) -> str:
    values = poster_values(
        title_en=chrome.get("title_en") or copy["screen_title"],
        title_zh=copy["screen_title"],
        summary_zh=chrome.get("summary_zh", ""),
        insight_1=chrome.get("insight_1", ""),
        insight_2=chrome.get("insight_2", ""),
        insight_3=chrome.get("insight_3", ""),
        speaker=chrome.get("speaker", ""),
        event=(chrome.get("event") or chrome.get("source") or chrome.get("stamp", "")),
        organization=chrome.get("organization", ""),
        verification=chrome.get("verification", ""),
        kicker="TECHNICAL HIGHLIGHTS",
        index=chrome.get("index", ""),
        series=chrome.get("series", ""),
        accent=chrome["accent"])
    return render_template(INTRO_TEMPLATE, values)


def render_poster_html(values: dict[str, str], out_dir: Path,
                       browser_arg: str | None = None) -> tuple[Path, Path]:
    html_text = render_template(INTRO_TEMPLATE, values)
    html_path = out_dir / "poster.html"
    png_path = out_dir / "poster.png"
    html_path.write_text(html_text, encoding="utf-8")
    browser = find_browser(browser_arg)
    if browser is None:
        raise RuntimeError("no Chrome/Edge found for the poster screenshot")
    render_html_to_png(html_path, png_path, browser=browser,
                       width=int(POSTER_DEFAULTS["width"]),
                       height=int(POSTER_DEFAULTS["height"]))
    return html_path, png_path


def build_poster_command(*, png: Path, out: Path, duration_ms: int,
                         voice: Path | None, cfg: dict[str, Any] | None = None,
                         gain: float = 1.0) -> list[str]:
    cfg = {**POSTER_DEFAULTS, **(cfg or {})}
    fps = int(cfg["fps"])
    duration = duration_ms / 1000.0
    frames = max(1, round(duration * fps))
    cmd = ["ffmpeg", "-hide_banner", "-y",
           "-loop", "1", "-framerate", str(fps), "-t", f"{duration:.3f}",
           "-i", str(png)]
    if voice is not None:
        cmd += ["-i", str(voice)]
        audio = (f"volume={gain:.4f},adelay={int(cfg['lead_ms'])}|{int(cfg['lead_ms'])},"
                 f"apad,atrim=0:{duration:.3f},aresample={int(cfg['audio_sample_rate'])},"
                 "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 "asetpts=PTS-STARTPTS,alimiter=limit=0.95")
    else:
        cmd += ["-f", "lavfi", "-t", f"{duration:.3f}",
                "-i", f"anullsrc=r={int(cfg['audio_sample_rate'])}:cl=stereo"]
        audio = (f"aresample={int(cfg['audio_sample_rate'])},"
                 "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"apad,atrim=0:{duration:.3f},asetpts=PTS-STARTPTS")
    cmd += ["-map", "0:v:0", "-map", "1:a:0",
            "-vf", f"fps={fps},format=yuv420p",
            "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]),
            "-preset", "slow", "-r", str(fps), "-frames:v", str(frames),
            "-af", audio, "-c:a", "aac", "-b:a", cfg["audio_bitrate"],
            "-ar", str(int(cfg["audio_sample_rate"])), "-ac", "2",
            "-t", f"{duration:.3f}", "-shortest",
            "-sn", "-dn", "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero", str(out)]
    return cmd


def build_card_html(*, index: str, title: str, kicker: str = "高光片段",
                    accent: str = DEFAULTS["accent"], series: str = "") -> str:
    values = {
        "ACCENT": accent,
        "INDEX": html.escape(index),
        "TITLE": html.escape(title),
        "KICKER": html.escape(kicker),
        "SERIES": html.escape(series),
        "SOURCE": html.escape(series),
    }
    return render_template(CARD_TEMPLATE, values)


# --------------------------------------------------------------------------
# picture rendering
# --------------------------------------------------------------------------
def find_browser(explicit: str | None = None) -> Path | None:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("INTRO_BROWSER")
    if env:
        candidates.append(env)
    candidates.extend(BROWSERS)
    for name in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def render_html_to_png(html_path: Path, png_path: Path, *, browser: Path,
                       width: int, height: int, timeout: int = 90) -> dict[str, Any]:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="intro-profile-") as profile:
        base = [
            str(browser),
            "--disable-gpu", "--hide-scrollbars",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--force-device-scale-factor=1", "--window-size=%d,%d" % (width, height),
            "--virtual-time-budget=2000", "--run-all-compositor-stages-before-draw",
            "--user-data-dir=%s" % profile,
        ]
        errors: list[str] = []
        for headless in (["--headless=new"], ["--headless"]):
            cmd = [base[0], *headless, *base[1:],
                   "--screenshot=%s" % png_path.resolve().as_posix(),
                   html_path.resolve().as_uri()]
            proc = run_cmd(cmd, timeout=timeout)
            if proc.returncode == 0 and png_path.exists() and png_path.stat().st_size > 0:
                return {"mode": "html", "browser": str(browser), "png": rel(png_path),
                        "command": cmd}
            errors.append((proc.stderr or proc.stdout).strip()[-400:])
        raise RuntimeError("headless screenshot failed: " + " | ".join(errors))


def _wrap_drawtext(text: str, per_line: int) -> str:
    text = " ".join(text.split())
    if len(text) <= per_line:
        return text
    lines, current = [], ""
    for ch in text:
        current += ch
        if len(current) >= per_line and ch in "，。！？、；：,.!?;: ":
            lines.append(current.strip())
            current = ""
    if current.strip():
        lines.append(current.strip())
    return "\n".join(lines)


def render_drawtext_to_png(*, out_path: Path, work_dir: Path,
                           copy: dict[str, str], chrome: dict[str, str],
                           width: int, height: int) -> dict[str, Any]:
    """Static fallback with the same palette when no browser is available."""
    font = next((p for p in FONT_CANDIDATES if Path(p).is_file()), None)
    if not font:
        raise RuntimeError("no CJK font found for the drawtext fallback")
    work_dir.mkdir(parents=True, exist_ok=True)
    parts = {
        "series": chrome["series"],
        "title": _wrap_drawtext(copy["screen_title"], 15),
        "subtitle": _wrap_drawtext(copy["screen_subtitle"], 30),
        "speaker": chrome["speaker"],
        "source": chrome["source"],
    }
    for name, text in parts.items():
        (work_dir / f"drawtext-{name}.txt").write_text(text, encoding="utf-8")
    font_arg = filter_path(Path(font))
    d = {k: filter_path(work_dir / f"drawtext-{k}.txt") for k in parts}
    accent = chrome["accent"].lstrip("#")
    draw = ";".join([
        f"drawbox=x=0:y=0:w=4:h={height}:color=0x{accent}@0.95:t=fill",
        f"drawtext=fontfile='{font_arg}':textfile='{d['series']}':"
        "fontcolor=0x93a0b1:fontsize=19:x=120:y=82",
        f"drawtext=fontfile='{font_arg}':textfile='{d['title']}':"
        "fontcolor=0xf2f5f8:fontsize=96:line_spacing=18:x=120:y=330",
        f"drawtext=fontfile='{font_arg}':textfile='{d['subtitle']}':"
        "fontcolor=0x93a0b1:fontsize=32:line_spacing=14:x=120:y=700",
        f"drawtext=fontfile='{font_arg}':textfile='{d['speaker']}':"
        "fontcolor=0x5e6b7c:fontsize=20:x=120:y=820",
        f"drawtext=fontfile='{font_arg}':textfile='{d['source']}':"
        "fontcolor=0x5e6b7c:fontsize=19:x=120:y=980",
    ])
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-f", "lavfi", "-i", f"color=c=0x0b0e13:s={width}x{height}:d=1",
        "-vf", draw, "-frames:v", "1", str(out_path),
    ]
    proc = run_cmd(cmd, timeout=120)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError("drawtext render failed: " + proc.stderr.strip()[-400:])
    return {"mode": "drawtext", "browser": None, "png": rel(out_path), "command": cmd}


def render_card_drawtext(*, out_path: Path, work_dir: Path, index: str, title: str,
                         kicker: str, series: str, accent: str,
                         width: int, height: int) -> dict[str, Any]:
    """Fallback transition card in the same industrial palette."""
    font = next((p for p in FONT_CANDIDATES if Path(p).is_file()), None)
    if not font:
        raise RuntimeError("no CJK font found for the drawtext fallback")
    work_dir.mkdir(parents=True, exist_ok=True)
    parts = {
        "index": index,
        "title": _wrap_drawtext(title, 16),
        "kicker": kicker,
        "series": series,
    }
    for name, text in parts.items():
        (work_dir / f"card-{name}.txt").write_text(text, encoding="utf-8")
    font_arg = filter_path(Path(font))
    d = {k: filter_path(work_dir / f"card-{k}.txt") for k in parts}
    accent_hex = accent.lstrip("#")
    draw = ";".join([
        f"drawbox=x=0:y=0:w=4:h={height}:color=0x{accent_hex}@0.95:t=fill",
        f"drawtext=fontfile='{font_arg}':textfile='{d['series']}':"
        "fontcolor=0x93a0b1:fontsize=19:x=120:y=82",
        f"drawtext=fontfile='{font_arg}':textfile='{d['index']}':"
        f"fontcolor=0x{accent_hex}:fontsize=170:x=160:y=400",
        f"drawtext=fontfile='{font_arg}':textfile='{d['kicker']}':"
        "fontcolor=0x93a0b1:fontsize=21:x=620:y=440",
        f"drawtext=fontfile='{font_arg}':textfile='{d['title']}':"
        "fontcolor=0xf2f5f8:fontsize=64:line_spacing=16:x=620:y=500",
    ])
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-f", "lavfi", "-i", f"color=c=0x0b0e13:s={width}x{height}:d=1",
        "-vf", draw, "-frames:v", "1", str(out_path),
    ]
    proc = run_cmd(cmd, timeout=120)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError("card drawtext render failed: " + proc.stderr.strip()[-400:])
    return {"mode": "drawtext", "browser": None, "png": rel(out_path), "command": cmd}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_keyframes(*, out_dir: Path, renderer: str, browser: Path | None,
                     cfg: dict[str, Any], copy: dict[str, str],
                     chrome: dict[str, str], style: str = "classic") -> dict[str, Any]:
    """Poster: one static frame.  Classic: state 0 and state 1."""
    if style == "poster":
        html_text = build_poster_html(copy=copy, chrome=chrome)
        html_path = out_dir / "intro.html"
        png_path = out_dir / "intro.png"
        html_path.write_text(html_text, encoding="utf-8")
        if renderer == "drawtext" or browser is None:
            raise RuntimeError("the poster template needs a headless browser")
        render_html_to_png(html_path, png_path, browser=browser,
                           width=cfg["width"], height=cfg["height"],
                           timeout=int(DEFAULTS["browser_timeout_s"]))
        return {"mode": "poster", "frames": [png_path], "html": [html_path],
                "png": png_path, "browser": str(browser),
                "hashes": [_sha256(png_path)], "info": None}
    final_html = build_intro_html(copy=copy, chrome=chrome, state=1)
    (out_dir / "intro.html").write_text(final_html, encoding="utf-8")

    if renderer == "drawtext" or browser is None:
        png_path = out_dir / "intro.png"
        info = render_drawtext_to_png(
            out_path=png_path, work_dir=out_dir / "work",
            copy=copy, chrome=chrome, width=cfg["width"], height=cfg["height"])
        return {"mode": "static", "frames": [png_path], "html": [out_dir / "intro.html"],
                "png": png_path, "browser": None, "hashes": [_sha256(png_path)],
                "info": info}

    frames: list[Path] = []
    htmls: list[Path] = []
    for state in (0, 1):
        html_text = build_intro_html(copy=copy, chrome=chrome, state=state)
        html_path = out_dir / ("intro.html" if state == 1 else "keyframe-0.html")
        png_path = out_dir / ("intro.png" if state == 1 else "keyframe-0.png")
        html_path.write_text(html_text, encoding="utf-8")
        render_html_to_png(html_path, png_path, browser=browser,
                           width=cfg["width"], height=cfg["height"],
                           timeout=int(DEFAULTS["browser_timeout_s"]))
        frames.append(png_path)
        htmls.append(html_path)
    hashes = [_sha256(path) for path in frames]
    if len(set(hashes)) != len(hashes):
        raise RuntimeError("keyframes are not distinct; the template state did not render")
    return {"mode": "keyframes", "frames": frames, "html": htmls,
            "png": frames[-1], "browser": str(browser), "hashes": hashes, "info": None}


# --------------------------------------------------------------------------
# voice
# --------------------------------------------------------------------------
def pad_head(path: Path, ms: int) -> None:
    """Prepend ``ms`` of silence in place so the intro never speaks on frame zero."""
    ms = int(ms)
    if ms <= 0:
        return
    tmp = path.with_suffix(".pad" + path.suffix)
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-y", "-i", str(path),
         "-af", f"adelay={ms}:all=1", "-c:a", "pcm_s16le", str(tmp)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300)
    if proc.returncode != 0:
        raise StageError(f"head-silence pad failed: {proc.stderr.strip()[-300:]}")
    tmp.replace(path)


def synthesize_voice(*, text: str, out_dir: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    log(f"waiting for CosyVoice at {cfg['base_url']} ...")
    health = sd.wait_for_service(cfg["base_url"], int(cfg["wait_s"]))
    log(f"service ready: model={health.get('model_class')} device={health.get('device')} "
        f"sample_rate={health.get('sample_rate')}")

    speaker = (cfg.get("voice_speaker") or "").strip()
    prompt_path = resolve(cfg["prompt_wav"])
    prompt_wav = "" if speaker else str(prompt_path)
    raw_path = out_dir / "narration.raw.wav"
    final_path = out_dir / "narration.wav"

    tts_text = sd.normalize_for_tts(text)
    script = [{
        "sentence_id": 1,
        "target_start_sec": 0.0,
        "max_duration_sec": cfg["voice_budget_ms"] / 1000,
        "text": tts_text,
    }]
    (out_dir / "intro.script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audio = sd.tts_request(cfg["base_url"], tts_text, prompt_wav, None,
                           int(cfg["tts_timeout_s"]), speaker=speaker or None)
    raw_path.write_bytes(audio)
    raw_s = sd.probe_duration(raw_path)

    tempo = tempo_for(round(raw_s * 1000), cfg)
    if tempo > 1.0:
        sd.apply_tempo(raw_path, final_path, tempo)
    else:
        shutil.copyfile(raw_path, final_path)
    head_ms = int(cfg.get("voice_head_silence_ms") or 0)
    pad_head(final_path, head_ms)
    final_s = sd.probe_duration(final_path)
    log(f"voice: raw {raw_s:.2f}s -> {final_s:.2f}s (tempo {tempo:.2f}x, "
        f"head silence {head_ms}ms)")
    return {
        "text": text,
        "tts_text": tts_text,
        "script": rel(out_dir / "intro.script.json"),
        "raw_path": rel(raw_path),
        "raw_seconds": round(raw_s, 3),
        "path": rel(final_path),
        "final_seconds": round(final_s, 3),
        "tempo": round(tempo, 4),
        "head_silence_ms": head_ms,
        "prompt_wav": rel(prompt_path) if prompt_wav else "",
        "voice_speaker": speaker,
        "service": {k: health.get(k) for k in
                    ("model_class", "model_dir", "device", "sample_rate", "text_frontend")},
    }


# --------------------------------------------------------------------------
# composition + acceptance
# --------------------------------------------------------------------------
def build_render_command(*, frames: list[Path], voice: Path, out: Path,
                         timeline: dict[str, int], animation: dict[str, int | float],
                         cfg: dict[str, Any], gain: float,
                         poster: bool = False) -> list[str]:
    width, height, fps = int(cfg["width"]), int(cfg["height"]), int(cfg["fps"])
    # Snap the duration to a whole number of frames so video and audio can be
    # cut at exactly the same instant (no dangling stream in the mux).
    frame_count = max(1, round(timeline["duration_ms"] / 1000.0 * fps))
    dur = frame_count / fps
    lead_ms = int(timeline["lead_ms"])
    bar = animation["bar_reveal_ms"] / 1000.0
    delay = animation["title_delay_ms"] / 1000.0
    fade = animation["title_fade_ms"] / 1000.0
    fade_in = animation["fade_in_ms"] / 1000.0
    fade_out = animation["fade_out_ms"] / 1000.0
    zoom = float(animation["ken_burns_per_sec"])
    accent = str(cfg["accent"]).lstrip("#")

    count = 1 if poster else min(len(frames), 2)   # poster = one static frame
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for frame in frames[:count]:
        cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(frame)]
    cmd += ["-i", str(voice)]
    voice_idx = count

    tail = (
        f"trim=duration={dur:.3f},setpts=PTS-STARTPTS,"
        f"zoompan=z='min(1+{zoom:.6f}*on/{fps},1.03)':d=1:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={width}x{height}:fps={fps},"
        f"drawbox=x=0:y=0:w=4:h='min(t/{bar:.3f},1)*ih':"
        f"color=0x{accent}@0.95:t=fill,"
        f"fade=t=in:st=0:d={fade_in:.3f},"
        f"fade=t=out:st={max(dur - fade_out, 0):.3f}:d={fade_out:.3f},"
        f"format=yuv420p[v]"
    )
    audio = (
        f"[{voice_idx}:a]volume={gain:.4f},"
        f"adelay={lead_ms}|{lead_ms},apad,atrim=0:{dur:.3f},"
        f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"alimiter=limit=0.95[a]"
    )
    if poster:
        graph = (
            f"[0:v]fps={fps},format=yuv420p,settb=AVTB,"
            f"trim=duration={dur:.3f},setpts=PTS-STARTPTS[v];{audio}"
        )
    elif count >= 2:
        graph = (
            f"[0:v]fps={fps},format=yuv420p,settb=AVTB[v0];"
            f"[1:v]fps={fps},format=yuv420p,settb=AVTB[v1];"
            f"[v0][v1]xfade=transition=fade:duration={fade:.3f}:offset={delay:.3f}[x];"
            f"[x]{tail};{audio}"
        )
    else:
        graph = (
            f"[0:v]fps={fps},format=yuv420p,settb=AVTB,{tail};{audio}"
        )

    return cmd + [
        "-filter_complex", graph,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]), "-preset", "slow",
        "-r", str(fps), "-frames:v", str(frame_count),
        "-c:a", "aac", "-b:a", cfg["audio_bitrate"],
        "-ar", str(cfg["audio_sample_rate"]), "-ac", "2",
        "-t", f"{dur:.6f}",
        "-shortest", "-sn", "-dn", "-movflags", "+faststart",
        "-avoid_negative_ts", "make_zero",
        str(out),
    ]


def verify_intro(path: Path, expected_ms: int, cfg: dict[str, Any],
                 frames: list[Path] | None = None,
                 copy: dict[str, str] | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    exists = path.exists() and path.stat().st_size > 0
    add("file_exists", exists, rel(path) if exists else "missing or empty")
    if not exists:
        return {"passed": False, "checks": checks}

    proc = run_cmd(["ffprobe", "-v", "error", "-print_format", "json",
                    "-show_format", "-show_streams", str(path)], timeout=60)
    data = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout else None
    add("probe", data is not None, "ffprobe parsed" if data else "ffprobe failed")
    if data is None:
        return {"passed": False, "checks": checks}

    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    add("has_video", video is not None, (video or {}).get("codec_name", "no video stream"))
    add("has_audio", audio is not None, (audio or {}).get("codec_name", "no audio stream"))
    add("video_codec", bool(video) and video.get("codec_name") == "h264",
        (video or {}).get("codec_name", ""))
    add("audio_codec", bool(audio) and audio.get("codec_name") == "aac",
        (audio or {}).get("codec_name", ""))
    extras = [s for s in streams if s.get("codec_type") not in ("video", "audio")]
    add("only_av_streams", not extras, "video + audio only" if not extras else str(extras))

    actual_ms = int(round(float(data["format"]["duration"]) * 1000))
    video_ms = int(round(float((video or {}).get("duration") or 0) * 1000))
    audio_ms = int(round(float((audio or {}).get("duration") or 0) * 1000))
    add("av_duration_equal",
        bool(video_ms and audio_ms
             and abs(video_ms - audio_ms) <= int(cfg["av_tolerance_ms"])),
        f"video {video_ms} ms vs audio {audio_ms} ms "
        f"(delta {video_ms - audio_ms:+d}, tolerance {cfg['av_tolerance_ms']})")
    audio_start_ms = int(round(float((audio or {}).get("start_time") or 0) * 1000))
    add("audio_starts_at_zero", abs(audio_start_ms) <= 60,
        f"audio start {audio_start_ms} ms")
    add("duration_window",
        int(cfg["min_duration_ms"]) <= actual_ms <= int(cfg["max_duration_ms"]),
        f"actual {actual_ms} ms, window [{cfg['min_duration_ms']}, {cfg['max_duration_ms']}]")
    add("duration_target", abs(actual_ms - expected_ms) <= int(cfg["tolerance_ms"]),
        f"actual {actual_ms} ms vs planned {expected_ms} ms "
        f"(delta {actual_ms - expected_ms:+d})")
    if video:
        add("resolution", (video.get("width"), video.get("height")) ==
            (int(cfg["width"]), int(cfg["height"])),
            f"{video.get('width')}x{video.get('height')}")
        try:
            actual_fps = float(Fraction(str(video.get("r_frame_rate", "0/1"))))
        except (ValueError, ZeroDivisionError):
            actual_fps = 0.0
        add("fps", abs(actual_fps - float(cfg["fps"])) < 0.01,
            f"{video.get('r_frame_rate')} ({actual_fps:.2f} fps), expected {cfg['fps']}")

    if frames:
        add("keyframes_exist", all(p.exists() and p.stat().st_size > 0 for p in frames),
            f"{len(frames)} frame(s): " + ", ".join(rel(p) for p in frames))
        if len(frames) > 1:
            hashes = [_sha256(p) for p in frames if p.exists()]
            add("keyframes_distinct", len(set(hashes)) == len(frames),
                f"{len(set(hashes))} distinct of {len(frames)}")

    if copy is not None:
        try:
            normalize_copy(copy, cfg)
            add("copy_structure", True,
                f"3 sentences, {_plain_len(copy['intro_spoken_text'])} chars, no hype words")
        except Exception as exc:
            add("copy_structure", False, str(exc))

    level = dub_mix.mean_volume_db(path)
    add("voice_audible", level is not None and level > -50.0,
        f"mean volume {level} dB" if level is not None else "no measurable audio")

    return {"passed": all(c["ok"] for c in checks), "checks": checks,
            "actual_duration_ms": actual_ms, "audio_mean_db": level}


# --------------------------------------------------------------------------
# stages
#
# Each stage is independently runnable and touches exactly one heavyweight
# resource.  They never start a service themselves: run_pipeline.py owns the
# lifecycle (start -> health poll -> stage -> taskkill /F /T -> 2 s cooldown).
# --------------------------------------------------------------------------
class StageError(RuntimeError):
    """A stage could not produce its artifact."""


class VoiceWindowError(StageError):
    """The narration cannot be placed inside the 6.0-9.5 s window."""

    def __init__(self, message: str, *, voice_ms: int, raw_seconds: float,
                 final_seconds: float | None = None, tempo: float = 1.0) -> None:
        super().__init__(message)
        self.voice_ms = voice_ms
        self.raw_seconds = raw_seconds
        self.final_seconds = final_seconds
        self.tempo = tempo


def save_copy(out_dir: Path, copy_info: dict[str, Any],
              normalized: dict[str, str]) -> dict[str, Any]:
    merged = {**copy_info, **normalized}
    write_json(out_dir / "copy.json",
               {k: v for k, v in merged.items() if k not in ("attempts", "prompt")})
    return merged


def load_copy(out_dir: Path, cfg: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    path = out_dir / "copy.json"
    if not path.exists():
        raise StageError(f"copy.json missing in {rel(out_dir)}; run the copy stage first")
    saved = json.loads(path.read_text(encoding="utf-8"))
    return normalize_copy(saved, cfg), saved


def load_narration(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "narration.json"
    if not path.exists():
        raise StageError(f"narration.json missing in {rel(out_dir)}; run the voice stage first")
    return json.loads(path.read_text(encoding="utf-8"))


def stage_copy(*, out_dir: Path, cfg: dict[str, Any], title: str = "",
               summary: str = "", copy_json: str | Path | None = None,
               copy_source: str = "llm", spoken_text: str = "",
               screen_title: str = "", screen_subtitle: str = "") -> dict[str, Any]:
    """Stage 1b: the 5W1H copy from local Qwen (or a saved JSON).

    Requires llama-server on 127.0.0.1:8080 unless ``copy_json`` is reused.
    Returns ``{"copy": normalized, "info": copy_info}`` and writes copy.json.
    """
    if copy_json:
        copy_path = resolve(copy_json)
        if not copy_path.exists():
            raise StageError(f"copy json not found: {copy_path}")
        saved = json.loads(copy_path.read_text(encoding="utf-8"))
        normalized = normalize_copy(saved, cfg)
        source_rel = rel(copy_path)
        reused_from = (source_rel if copy_path.resolve() !=
                       (out_dir / "copy.json").resolve() else None)
        copy_info: dict[str, Any] = {"source": saved.get("source", "llm"),
                                     "model": saved.get("model"),
                                     "base_url": saved.get("base_url"),
                                     "prompt": None, "attempts": []}
        if reused_from:
            copy_info["reused_from"] = reused_from
        copy_info.update(normalized)
    elif copy_source == "llm":
        if not title.strip() and not summary.strip():
            raise StageError("--title or --summary is required for the local Qwen")
        copy_info = generate_copy_llm(title=title, summary=summary, cfg=cfg)
        normalized = {k: copy_info[k] for k in
                      ("intro_spoken_text", "screen_title", "screen_subtitle")}
    else:
        spoken = spoken_text.strip() or title.strip()
        stitle = screen_title.strip() or title.strip()
        subtitle = screen_subtitle.strip()
        if not spoken or not stitle or not subtitle:
            raise StageError("--copy-source args needs --spoken-text, --screen-title "
                             "and --screen-subtitle (or --title fallbacks)")
        normalized = normalize_copy({"intro_spoken_text": spoken,
                                     "screen_title": stitle,
                                     "screen_subtitle": subtitle}, cfg)
        copy_info = {"source": "args", "model": None, "base_url": None,
                     "prompt": None, "attempts": [], **normalized}

    if spoken_text.strip():
        normalized["intro_spoken_text"] = spoken_text.strip()
    if screen_title.strip():
        normalized["screen_title"] = screen_title.strip()
    if screen_subtitle.strip():
        normalized["screen_subtitle"] = screen_subtitle.strip()
    normalized = normalize_copy(normalized, cfg)
    copy_info = {**copy_info, **normalized}

    if copy_info.get("prompt"):
        (out_dir / "copy.prompt.txt").write_text(copy_info["prompt"], encoding="utf-8")
    if copy_info.get("attempts"):
        write_json(out_dir / "copy.response.json", {"attempts": copy_info["attempts"]})
    save_copy(out_dir, copy_info, normalized)
    log(f"copy: {normalized['intro_spoken_text']}")
    return {"copy": normalized, "info": copy_info}


def stage_rewrite(*, out_dir: Path, cfg: dict[str, Any],
                  copy: dict[str, str]) -> dict[str, Any]:
    """Stage 1 repair: ask Qwen for a shorter spoken line after a TTS overshoot.

    Runs in a fresh LLM window (CosyVoice is already dead), so the serial rule
    holds even for the repair path.
    """
    rewrite = rewrite_copy_llm(spoken=copy["intro_spoken_text"], cfg=cfg)
    (out_dir / "copy_rewrite.prompt.txt").write_text(rewrite["prompt"], encoding="utf-8")
    write_json(out_dir / "copy_rewrite.response.json", {"attempts": rewrite["attempts"]})
    updated = normalize_copy({**copy, "intro_spoken_text": rewrite["text"]}, cfg)
    log(f"copy rewrite: {updated['intro_spoken_text']}")
    return {"copy": updated, "prompt": rewrite["prompt"]}


def stage_voice(*, out_dir: Path, cfg: dict[str, Any], text: str,
                voice_wav: str | Path | None = None) -> dict[str, Any]:
    """Stage 2: one CosyVoice request + the 6.0-9.5 s duration audit.

    atempo (capped at ``max_tempo``) is the only correction allowed here; a
    line that still overflows raises ``VoiceWindowError`` so the orchestrator
    can reopen the LLM window and rewrite it.
    """
    if voice_wav:
        voice_path = resolve(voice_wav)
        if not voice_path.exists():
            raise StageError(f"voice wav not found: {voice_path}")
        voice_s = sd.probe_duration(voice_path)
        voice_info: dict[str, Any] = {
            "text": text, "script": None, "raw_path": rel(voice_path),
            "raw_seconds": round(voice_s, 3), "path": rel(voice_path),
            "final_seconds": round(voice_s, 3), "tempo": 1.0,
            "prompt_wav": None, "service": {"reused": True},
        }
    else:
        voice_info = synthesize_voice(text=text, out_dir=out_dir, cfg=cfg)

    voice_ms = round(float(voice_info["final_seconds"]) * 1000)
    # The head silence is baked into narration.wav, so the timeline lead must be
    # zero; otherwise picture-vs-voice pre-roll becomes 200 + 600 ms.
    timeline_cfg = cfg
    if int(voice_info.get("head_silence_ms") or 0) > 0:
        timeline_cfg = {**cfg, "lead_ms": 0}
    try:
        timeline = plan_timeline(voice_ms, timeline_cfg)
    except ValueError as exc:
        raise VoiceWindowError(
            str(exc), voice_ms=voice_ms,
            raw_seconds=float(voice_info.get("raw_seconds") or 0.0),
            final_seconds=float(voice_info.get("final_seconds") or 0.0),
            tempo=float(voice_info.get("tempo") or 1.0)) from exc
    write_json(out_dir / "narration.json", voice_info)
    log(f"voice: {timeline['voice_ms']} ms inside {timeline['duration_ms']} ms "
        f"(lead {timeline['lead_ms']} + tail {timeline['tail_ms']})")
    return {"voice": voice_info, "timeline": timeline}


def stage_picture(*, out_dir: Path, cfg: dict[str, Any], copy: dict[str, str],
                  chrome: dict[str, str], renderer: str = "auto",
                  browser_arg: str | None = None) -> dict[str, Any]:
    """Stage 3: fixed industrial template -> two deterministic PNG states."""
    style = str(cfg.get("intro_style", "classic"))
    browser = find_browser(browser_arg) if renderer in ("auto", "html") else None
    if (renderer == "html" or style == "poster") and browser is None:
        raise StageError("--renderer html/--intro-style poster but no Chrome/Edge found")
    try:
        frames_info = render_keyframes(out_dir=out_dir, renderer=renderer,
                                       browser=browser, cfg=cfg, copy=copy,
                                       chrome=chrome, style=style)
    except Exception as exc:
        if renderer == "html" or style == "poster":
            raise StageError(f"keyframe render failed: {exc}") from exc
        log(f"keyframe render failed ({exc}); falling back to drawtext")
        frames_info = render_keyframes(out_dir=out_dir, renderer="drawtext",
                                       browser=None, cfg=cfg, copy=copy,
                                       chrome=chrome, style="classic")
    payload = {
        "mode": frames_info["mode"],
        "style": style,
        "frames": [rel(p) for p in frames_info["frames"]],
        "png": rel(frames_info["png"]),
        "hashes": frames_info.get("hashes", []),
        "browser": frames_info.get("browser"),
        "renderer": renderer,
    }
    write_json(out_dir / "picture.json", payload)
    log(f"picture: {frames_info['mode']} -> {len(frames_info['frames'])} frame(s)")
    return {**frames_info, "payload": payload}


def load_picture(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "picture.json"
    if not path.exists():
        raise StageError(f"picture.json missing in {rel(out_dir)}; run the picture stage")
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = [resolve(p) for p in payload.get("frames", [])]
    if not frames or not all(p.exists() for p in frames):
        raise StageError("keyframe PNGs are missing; rerun the picture stage")
    return {"mode": payload.get("mode", "keyframes"), "frames": frames,
            "png": resolve(payload.get("png") or payload["frames"][-1]),
            "browser": payload.get("browser"), "hashes": payload.get("hashes", []),
            "payload": payload}


def chrome_block(args: argparse.Namespace, cfg: dict[str, Any]) -> dict[str, str]:
    return {
        "series": args.series, "speaker": args.speaker, "source": args.source,
        "stamp": args.stamp, "stamp_right": args.stamp_right, "index": args.index,
        "eyebrow": args.eyebrow, "eyebrow_right": args.eyebrow_right,
        "accent": cfg["accent"],
        "title_en": getattr(args, "title_en", ""),
        "event": getattr(args, "event", ""),
        "organization": getattr(args, "organization", ""),
        "verification": getattr(args, "verification", ""),
        "summary_zh": getattr(args, "summary_zh", ""),
        "insight_1": getattr(args, "insight_1", ""),
        "insight_2": getattr(args, "insight_2", ""),
        "insight_3": getattr(args, "insight_3", ""),
    }


def stage_render(*, video_id: str, out_dir: Path, cfg: dict[str, Any],
                 copy: dict[str, str], copy_info: dict[str, Any],
                 chrome: dict[str, str], frames_info: dict[str, Any],
                 voice_info: dict[str, Any], timeline: dict[str, int],
                 update_result: bool = True) -> dict[str, Any]:
    """Stage 4a: QSV composition + ffprobe acceptance for the intro card."""
    voice_path = resolve(voice_info["path"])
    poster = str(cfg.get("intro_style", "classic")) == "poster"
    animation = plan_animation(timeline["duration_ms"], timeline["tail_ms"], cfg)
    log(f"timeline: lead {timeline['lead_ms']} + voice {timeline['voice_ms']} + "
        f"tail {timeline['tail_ms']} = {timeline['duration_ms']} ms")
    if poster:
        log(f"poster: one static frame, no zoom/drawbox/fade, fps {cfg['fps']}")
    else:
        log(f"animation: rail {animation['bar_reveal_ms']} ms, title +"
            f"{animation['title_delay_ms']} ms / {animation['title_fade_ms']} ms, "
            f"ken burns {animation['ken_burns_per_sec']}/s, fps {cfg['fps']}")

    gain = dub_mix.resolve_gain(voice_path, {"dub_target_db": DEFAULTS["dub_target_db"]})
    tmp_path = out_dir / "intro.tmp.mp4"
    intro_path = out_dir / "intro.mp4"
    cmd = build_render_command(frames=frames_info["frames"], voice=voice_path,
                               out=tmp_path, timeline=timeline, animation=animation,
                               cfg=cfg, gain=gain, poster=poster)
    log("$ " + " ".join(cmd))
    proc = run_cmd(cmd, timeout=900)
    if proc.returncode != 0:
        raise StageError(f"ffmpeg failed: {proc.stderr.strip()[-800:]}")

    acceptance = verify_intro(tmp_path, timeline["duration_ms"], cfg,
                              frames_info["frames"], copy)
    if acceptance["passed"]:
        os.replace(tmp_path, intro_path)
        status, target = "SUCCESS", intro_path
    else:
        target = out_dir / "intro.rejected.mp4"
        os.replace(tmp_path, target)
        status = "FAILED"
    failed = [c["name"] for c in acceptance["checks"] if not c["ok"]]
    log(f"acceptance: {'PASS' if acceptance['passed'] else 'FAIL ' + str(failed)} | "
        f"{acceptance.get('actual_duration_ms')} ms")

    record = {
        "schema_version": SCHEMA_VERSION,
        "video_id": video_id,
        "status": status,
        "generated_at": now_iso(),
        "path": rel(target) if status == "SUCCESS" else None,
        "quarantined": rel(target) if status != "SUCCESS" else None,
        "duration_ms": acceptance.get("actual_duration_ms"),
        "planned_duration_ms": timeline["duration_ms"],
        "manual_review": False,
        "target_platform": f"16:9 横屏 ({cfg['width']}x{cfg['height']}@{cfg['fps']}fps)",
        "accent": cfg["accent"],
        "template": rel(TEMPLATE_DIR / (INTRO_TEMPLATE if poster else CLASSIC_TEMPLATE)),
        "picture": {
            "renderer": ("poster" if poster else
                         ("html" if frames_info["mode"] == "keyframes" else "drawtext")),
            "animation": frames_info["mode"],
            "browser": frames_info.get("browser"),
            "html": rel(out_dir / "intro.html"),
            "png": rel(frames_info["png"]),
            "keyframes": [rel(p) for p in frames_info["frames"]],
            "headline": copy["screen_title"],
            "subline": copy["screen_subtitle"],
            "series": chrome["series"],
            "speaker": chrome["speaker"],
            "source": chrome["source"],
            "stamp": chrome["stamp"],
            "index": chrome["index"],
        },
        "copy": {k: v for k, v in copy_info.items()
                 if k not in ("attempts", "prompt")},
        "copy_prompt": (rel(out_dir / "copy.prompt.txt")
                        if (out_dir / "copy.prompt.txt").exists() else None),
        "copy_response": (rel(out_dir / "copy.response.json")
                          if (out_dir / "copy.response.json").exists() else None),
        "copy_rewrite_prompt": (rel(out_dir / "copy_rewrite.prompt.txt")
                                if (out_dir / "copy_rewrite.prompt.txt").exists() else None),
        "copy_rewrite_response": (rel(out_dir / "copy_rewrite.response.json")
                                  if (out_dir / "copy_rewrite.response.json").exists() else None),
        "animation": animation,
        "narration": voice_info,
        "timeline": timeline,
        "gain": round(gain, 4),
        "config": {k: cfg[k] for k in ("width", "height", "fps", "lead_ms", "tail_ms",
                                       "min_duration_ms", "max_duration_ms",
                                       "voice_budget_ms", "max_tempo", "qsv_quality",
                                       "audio_bitrate")},
        "acceptance": acceptance,
        "ffmpeg_command": cmd,
    }
    write_json(out_dir / "intro.json", record)

    if update_result:
        result_path = out_dir.parent / "result.json"
        if result_path.exists():
            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))
                data["intro"] = {k: record[k] for k in
                                 ("video_id", "status", "generated_at", "path",
                                  "quarantined", "duration_ms", "planned_duration_ms",
                                  "manual_review", "target_platform", "accent",
                                  "template", "picture", "copy", "copy_prompt",
                                  "copy_response", "copy_rewrite_prompt",
                                  "copy_rewrite_response", "animation", "narration",
                                  "timeline", "acceptance")}
                write_json(result_path, data)
            except Exception as exc:
                log(f"warning: could not update {rel(result_path)}: {exc}")

    log(f"intro status: {status}")
    log(f"intro file: {rel(target)}")
    if status != "SUCCESS":
        raise StageError(f"intro failed acceptance: {failed}")
    return record


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_cfg(args: argparse.Namespace) -> dict[str, Any]:
    cfg = {
        **DEFAULTS,
        "base_url": args.base,
        "prompt_wav": args.prompt_wav,
        "voice_speaker": (getattr(args, "voice_speaker", "") or "").strip(),
        "llm_base": args.llm_base,
        "llm_model": args.llm_model,
        "llm_timeout_s": args.llm_timeout,
        "llm_temperature": args.llm_temperature,
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "lead_ms": args.lead_ms,
        "tail_ms": args.tail_ms,
        "min_duration_ms": args.min_duration_ms,
        "max_duration_ms": args.max_duration_ms,
        "voice_budget_ms": args.voice_budget_ms,
        "max_tempo": args.max_tempo,
        "qsv_quality": args.qsv_quality,
        "audio_bitrate": args.audio_bitrate,
        "accent": args.accent,
        "intro_style": getattr(args, "intro_style", "classic"),
    }
    if cfg["intro_style"] == "poster":
        # Poster mode now targets 12-18 s: keep the voice under 16 s so a long
        # line still lands inside the 20 s ceiling.
        cfg["voice_budget_ms"] = min(int(args.voice_budget_ms), 16000)
    return cfg


def add_intro_arguments(ap: argparse.ArgumentParser) -> None:
    """Everything an intro needs; run_pipeline.py reuses this parser."""
    ap.add_argument("--video-id", default=None)
    ap.add_argument("--title", default="", help="episode title (context for local Qwen)")
    ap.add_argument("--summary", default="", help="episode summary (context for local Qwen)")
    ap.add_argument("--spoken-text", default="", help="override intro_spoken_text")
    ap.add_argument("--screen-title", default="", help="override screen_title")
    ap.add_argument("--screen-subtitle", default="", help="override screen_subtitle")
    ap.add_argument("--copy-source", choices=("llm", "args"), default="llm",
                    help="llm: local Qwen writes the 5W1H copy (default); "
                         "args: use --spoken-text/--screen-title/--screen-subtitle")
    ap.add_argument("--copy-json", default=None,
                    help="reuse a saved copy.json instead of calling Qwen again")
    ap.add_argument("--copy-only", action="store_true",
                    help="generate the copy and exit before rendering")
    ap.add_argument("--llm-base", default=DEFAULTS["llm_base"])
    ap.add_argument("--llm-model", default=DEFAULTS["llm_model"])
    ap.add_argument("--llm-timeout", type=int, default=DEFAULTS["llm_timeout_s"])
    ap.add_argument("--llm-temperature", type=float, default=DEFAULTS["llm_temperature"])
    ap.add_argument("--series", default="AI 基建", help="series label, top left")
    ap.add_argument("--speaker", default="", help="micro speaker stamp")
    ap.add_argument("--source", default="", help="bottom-left source line")
    ap.add_argument("--stamp", default="", help="top-right stamp")
    ap.add_argument("--stamp-right", default="", help="bottom-right stamp")
    ap.add_argument("--index", default="", help="top-right index, e.g. 021")
    ap.add_argument("--eyebrow", default="CONTEXT", help="small accent label")
    ap.add_argument("--eyebrow-right", default="FIELD RECORD", help="label after the slash")
    ap.add_argument("--accent", default=DEFAULTS["accent"], help="accent hex, e.g. #ff5500")
    ap.add_argument("--intro-style", choices=("poster", "classic"), default="poster",
                    help="poster: McKinsey orange/white static card (default); "
                         "classic: previous animated industrial template")
    ap.add_argument("--title-en", default="", help="English poster headline")
    ap.add_argument("--event", default="", help="poster source event, e.g. Daytona 2026")
    ap.add_argument("--organization", default="", help="poster organization")
    ap.add_argument("--verification", default="", help="poster verification line")
    ap.add_argument("--summary-zh", default="", help="poster one-line engineering summary")
    ap.add_argument("--insight-1", default="", help="poster insight 1")
    ap.add_argument("--insight-2", default="", help="poster insight 2")
    ap.add_argument("--insight-3", default="", help="poster insight 3")
    ap.add_argument("--out", default=None, help="default clips/<video_id>/intro")
    ap.add_argument("--base", default=DEFAULTS["base_url"])
    ap.add_argument("--prompt-wav", default=DEFAULTS["prompt_wav"])
    ap.add_argument("--voice-speaker", default=DEFAULTS["voice_speaker"],
                    help="SFT preset speaker id (e.g. 中文男); replaces the cloned reference")
    ap.add_argument("--renderer", choices=("auto", "html", "drawtext"), default="auto")
    ap.add_argument("--browser", default=None)
    ap.add_argument("--width", type=int, default=DEFAULTS["width"])
    ap.add_argument("--height", type=int, default=DEFAULTS["height"])
    ap.add_argument("--fps", type=int, default=DEFAULTS["fps"])
    ap.add_argument("--lead-ms", type=int, default=DEFAULTS["lead_ms"])
    ap.add_argument("--tail-ms", type=int, default=DEFAULTS["tail_ms"])
    ap.add_argument("--min-duration-ms", type=int, default=DEFAULTS["min_duration_ms"])
    ap.add_argument("--max-duration-ms", type=int, default=DEFAULTS["max_duration_ms"])
    ap.add_argument("--voice-budget-ms", type=int, default=DEFAULTS["voice_budget_ms"])
    ap.add_argument("--max-tempo", type=float, default=DEFAULTS["max_tempo"])
    ap.add_argument("--qsv-quality", type=int, default=DEFAULTS["qsv_quality"])
    ap.add_argument("--audio-bitrate", default=DEFAULTS["audio_bitrate"])
    ap.add_argument("--voice-wav", default=None,
                    help="reuse an existing narration WAV instead of calling CosyVoice")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate a local 6-9.5 s industrial intro")
    add_intro_arguments(ap)
    ap.add_argument("--stage", choices=("all", "copy", "rewrite", "voice", "picture",
                                        "render"), default="all",
                    help="run one stage only (default: the full serial pipeline)")
    ap.add_argument("--manage-services", action="store_true",
                    help="for a single stage: start/health-poll/kill the service "
                         "(default: assume it is already running)")
    args = ap.parse_args(argv)
    if not args.video_id:
        ap.error("--video-id is required")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = build_cfg(args)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", cfg["accent"]):
        print("config error: --accent must be #RRGGBB", file=sys.stderr)
        return 2
    if cfg["min_duration_ms"] < 1000 or cfg["max_duration_ms"] > 30000:
        print("config error: duration window looks wrong", file=sys.stderr)
        return 2
    if cfg["min_duration_ms"] >= cfg["max_duration_ms"]:
        print("config error: max-duration-ms must exceed min-duration-ms", file=sys.stderr)
        return 2

    out_dir = resolve(args.out) if args.out else ROOT / "clips" / args.video_id / "intro"
    out_dir.mkdir(parents=True, exist_ok=True)
    chrome = chrome_block(args, cfg)
    if args.copy_only and args.stage == "all":
        args.stage = "copy"     # historical flag: preview the copy and stop

    if args.stage == "all":
        # The full serial pipeline (LLM -> TTS -> picture -> QSV) lives in
        # run_pipeline.py; importing it lazily keeps the module graph acyclic.
        import run_pipeline
        return run_pipeline.intro_only(args, cfg, out_dir)

    try:
        if args.stage == "copy":
            if args.manage_services:
                import resource_manager as rm
                with rm.llama_server():
                    result = stage_copy(
                        out_dir=out_dir, cfg=cfg, title=args.title,
                        summary=args.summary, copy_json=args.copy_json,
                        copy_source=args.copy_source, spoken_text=args.spoken_text,
                        screen_title=args.screen_title,
                        screen_subtitle=args.screen_subtitle)
            else:
                result = stage_copy(
                    out_dir=out_dir, cfg=cfg, title=args.title, summary=args.summary,
                    copy_json=args.copy_json, copy_source=args.copy_source,
                    spoken_text=args.spoken_text, screen_title=args.screen_title,
                    screen_subtitle=args.screen_subtitle)
            normalized = result["copy"]
            log(f"title:   {normalized['screen_title']}")
            log(f"subtitle:{normalized['screen_subtitle']}")
            if args.copy_only:
                print(json.dumps({"source": result["info"]["source"],
                                  "model": result["info"].get("model"),
                                  **normalized}, ensure_ascii=False, indent=2))
            return 0
        if args.stage == "rewrite":
            copy, saved = load_copy(out_dir, cfg)
            if args.manage_services:
                import resource_manager as rm
                with rm.llama_server():
                    result = stage_rewrite(out_dir=out_dir, cfg=cfg, copy=copy)
            else:
                result = stage_rewrite(out_dir=out_dir, cfg=cfg, copy=copy)
            save_copy(out_dir, saved, result["copy"])
            return 0
        if args.stage == "voice":
            copy, _ = load_copy(out_dir, cfg)
            if args.manage_services:
                import resource_manager as rm
                with rm.cosyvoice(preset_voice=bool(cfg.get("voice_speaker"))):
                    stage_voice(out_dir=out_dir, cfg=cfg, text=copy["intro_spoken_text"],
                                voice_wav=args.voice_wav)
            else:
                stage_voice(out_dir=out_dir, cfg=cfg, text=copy["intro_spoken_text"],
                            voice_wav=args.voice_wav)
            return 0
        if args.stage == "picture":
            copy, _ = load_copy(out_dir, cfg)
            stage_picture(out_dir=out_dir, cfg=cfg, copy=copy, chrome=chrome,
                          renderer=args.renderer, browser_arg=args.browser)
            return 0
        if args.stage == "render":
            import resource_manager as rm
            copy, saved = load_copy(out_dir, cfg)
            voice_info = load_narration(out_dir)
            timeline = plan_timeline(round(float(voice_info["final_seconds"]) * 1000), cfg)
            frames_info = load_picture(out_dir)
            with rm.quiet_stage("intro render"):
                stage_render(video_id=args.video_id, out_dir=out_dir, cfg=cfg,
                             copy=copy, copy_info=saved, chrome=chrome,
                             frames_info=frames_info, voice_info=voice_info,
                             timeline=timeline)
            return 0
        print(f"unknown stage: {args.stage}", file=sys.stderr)
        return 2
    except Exception as exc:
        log(f"stage failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
