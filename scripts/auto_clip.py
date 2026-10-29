"""Pick highlight clips from a bilingual SRT and render them with FFmpeg/QSV.

The local LLM only proposes cue-ID ranges; every time calculation, ownership
check, overlap decision, quota and acceptance check is deterministic Python.

Usage:
    uv run python scripts/auto_clip.py \
        --srt subtitles/c88l8daXiv4.zh.bilingual.srt \
        --video "downloads/... [c88l8daXiv4].mkv"

    # analysis only, no rendering
    uv run python scripts/auto_clip.py --srt ... --analyze-only

See docs/自动剪辑-高光切片方案.md for the full specification.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_subs import clean, write_ass, write_srt  # noqa: E402
import dub_mix  # noqa: E402

SCHEMA_VERSION = 1
SRT_TS = re.compile(
    r"^\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)
TEXT_OK = re.compile(r"[\w一-鿿]", re.UNICODE)
SLUG_BAD = re.compile(r"[^\w一-鿿-]+", re.UNICODE)

DEFAULTS: dict[str, Any] = {
    "window_ms": 300_000,
    "overlap_ms": 60_000,
    "min_clip_ms": 45_000,
    "max_clip_ms": 90_000,       # ~1 min clips; 90 s is the emergency ceiling
    "prefer_min_ms": 50_000,
    "prefer_max_ms": 70_000,
    "dup_overlap_ratio": 0.4,
    "overlap_penalty_ms": 15_000,   # >15 s overlap with a kept candidate = strong penalty
    "max_clips": 5,
    "reel_budget_ms": 330_000,      # whole reel: intro + clips + transitions
    "intro_budget_ms": 15_000,      # 12-16 s poster intro, conservative estimate
    "transition_ms": 500,
    "duration_tolerance_ms": 1_500,
    "margin_v": 100,
    "qsv_quality": 19,
    "audio_bitrate": "160k",
    "video_codec": "h264",
    "audio_codec": "aac",
    "base_url": "http://127.0.0.1:8080",
    "model_timeout_s": 300,
    "model_retries": 2,
    "temperature": 0.1,
}

SYSTEM_PROMPT = (
    "你是一名资深科技视频剪辑师。你只输出一个严格合法的 JSON 对象，"
    "不输出解释、不输出 Markdown 代码块、不输出时间字段。"
)

# Boundary heuristics for complete-argument clips.  Automatic captions split
# mid-sentence, so these only *rank* candidates; the only hard reject is the
# double negative (filler start + non-terminal continuation end).
FILLER_START = re.compile(
    r"^(?:like|um+|uh+|yeah|okay|ok|right|so|and|but|well|i mean|you know)\b",
    re.I,
)
CONTINUATION_END = re.compile(
    r"(?:,|\band\b|\bbut\b|\bso\b|\bbecause\b|\bwhich\b|\bthat\b|\bif\b|\.\.\.)\s*$",
    re.I,
)
TERMINAL_END = re.compile(r'(?<!\.)[.?!][\'"]?\s*$')
DEPENDENT_START = re.compile(
    r"^(?:brought|which|that|because|but also|and then|also|however|as well as|and |but )\b",
    re.I,
)
# Spoken fillers that can be trimmed off the head of a cue instead of dropping
# the whole candidate.  Longest first so "yeah so" wins over "yeah".
FILLER_PREFIXES = ("yeah so", "yeah", "i mean", "you know", "um", "uh", "okay", "ok", "so")


# --------------------------------------------------------------------------
# logging / helpers
# --------------------------------------------------------------------------
class Run:
    def __init__(self) -> None:
        self.log_path: Path | None = None

    def log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        print(line, flush=True)
        if self.log_path is not None:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")


RUN = Run()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    RUN.log(f"wrote {rel(path)}")


def fmt_hmsms(ms: int) -> str:
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02}.{ms:03}"


def slugify(text: str, limit: int = 20) -> str:
    slug = SLUG_BAD.sub("-", text).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:limit].rstrip("-")


def parse_time_ms(value: str) -> int:
    """Accept HH:MM:SS.mmm, MM:SS.mmm, or an integer number of milliseconds."""
    value = value.strip()
    if re.fullmatch(r"\d+", value):
        return int(value)
    parts = value.split(":")
    if len(parts) == 3:
        h, m, rest = parts
    elif len(parts) == 2:
        h, m, rest = "0", parts[0], parts[1]
    else:
        raise ValueError(f"bad time: {value!r}")
    if "." in rest or "," in rest:
        sec, frac = re.split(r"[.,]", rest, maxsplit=1)
    else:
        sec, frac = rest, "0"
    try:
        hours, minutes, seconds = int(h), int(m), int(sec)
        millis = int(frac.ljust(3, "0")[:3])
    except ValueError as exc:
        raise ValueError(f"bad time: {value!r}") from exc
    if not (0 <= minutes < 60 and 0 <= seconds < 60):
        raise ValueError(f"bad time: {value!r}")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def parse_overrides(values: list[str]) -> dict[int, int]:
    """Parse repeated INDEX=TIME arguments (1-based clip index)."""
    overrides: dict[int, int] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"override must be INDEX=TIME, got {raw!r}")
        index_text, time_text = raw.split("=", 1)
        try:
            index = int(index_text)
        except ValueError as exc:
            raise ValueError(f"bad clip index: {index_text!r}") from exc
        if index < 1:
            raise ValueError("clip index must be >= 1")
        overrides[index] = parse_time_ms(time_text)
    return overrides


def snap_to_cue_start(cues: list[Cue], t_ms: int) -> tuple[int, int]:
    """Snap a manual start time to a cue boundary (containing cue, else nearest)."""
    for cue in cues:
        if cue.start <= t_ms < cue.end:
            return cue.id, cue.start
    nearest = min(cues, key=lambda c: (abs(c.start - t_ms), c.id))
    return nearest.id, nearest.start


def run_cmd(cmd: list[str], timeout: int, log_path: Path | None = None,
            cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    RUN.log("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=str(cwd))
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "$ " + " ".join(cmd) + "\n\n--- stdout ---\n" + proc.stdout
            + "\n--- stderr ---\n" + proc.stderr + f"\n--- exit {proc.returncode} ---\n",
            encoding="utf-8",
        )
    return proc


# --------------------------------------------------------------------------
# module 1: strict bilingual SRT parsing
# --------------------------------------------------------------------------
@dataclass
class Cue:
    id: int          # internal, 1-based, decoupled from SRT numbering
    start: int       # ms
    end: int         # ms
    top: str         # original language
    bottom: str      # Chinese (may be empty)


def _parse_ts(groups: tuple[str, ...]) -> int:
    h, m, s, ms = (int(g) for g in groups)
    if len(groups[3]) == 1:
        ms *= 100
    elif len(groups[3]) == 2:
        ms *= 10
    return h * 3_600_000 + m * 60_000 + s * 1_000 + ms


def parse_bilingual_srt(path: Path) -> tuple[list[Cue], list[dict[str, Any]]]:
    """Strict parser: integer-ms cues, per-block errors, original/Chinese split."""
    errors: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8-sig", errors="strict")
    except (OSError, UnicodeDecodeError) as exc:
        return [], [{"stage": "read", "error": str(exc)}]

    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n").replace("\r", "\n").strip())
    cues: list[Cue] = []
    prev_start = -1
    for idx, block in enumerate(blocks, 1):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if re.fullmatch(r"\d+", lines[0].strip()) and len(lines) > 1:
            lines = lines[1:]
        match = SRT_TS.match(lines[0]) if lines else None
        if not match:
            errors.append({"stage": "timestamp", "block": idx,
                           "error": f"cannot parse timestamp line: {lines[:1]}"})
            continue
        start = _parse_ts(match.groups()[:4])
        end = _parse_ts(match.groups()[4:])
        text_lines = [clean(ln) for ln in lines[1:]]
        text_lines = [ln for ln in text_lines if ln]
        if not text_lines:
            errors.append({"stage": "text", "block": idx, "error": "empty cue text"})
            continue
        top = text_lines[0]
        bottom = " ".join(text_lines[1:])
        if start >= end:
            errors.append({"stage": "order", "block": idx,
                           "error": f"start {start} >= end {end}"})
            continue
        if start < prev_start:
            errors.append({"stage": "monotonic", "block": idx,
                           "error": f"start {start} < previous {prev_start}"})
            continue
        if not TEXT_OK.search(top):
            errors.append({"stage": "text", "block": idx,
                           "error": "text has no word characters"})
            continue
        prev_start = start
        cues.append(Cue(id=len(cues) + 1, start=start, end=end, top=top, bottom=bottom))

    if not cues and not errors:
        errors.append({"stage": "content", "error": "no cues found"})
    return cues, errors


# --------------------------------------------------------------------------
# module 2: real-time sliding windows
# --------------------------------------------------------------------------
@dataclass
class Window:
    index: int
    start: int
    end: int
    cue_ids: list[int]


def build_windows(cues: list[Cue], window_ms: int, overlap_ms: int,
                  min_clip_ms: int) -> list[Window]:
    last_end = cues[-1].end
    step = window_ms - overlap_ms
    if step <= 0:
        raise ValueError("overlap_ms must be smaller than window_ms")
    windows: list[Window] = []
    start = 0
    while start < last_end:
        end = min(start + window_ms, last_end)
        if end - start >= min_clip_ms or not windows:
            ids = [c.id for c in cues if c.start < end and c.end > start]
            if ids:
                windows.append(Window(index=len(windows), start=start, end=end, cue_ids=ids))
        if start + window_ms >= last_end:
            break
        start += step
    return windows


# --------------------------------------------------------------------------
# module 3: single-window model inference
# --------------------------------------------------------------------------
def _window_header(win: Window, cues: list[Cue]
                   ) -> tuple[list[str], list[Cue]]:
    by_id = {c.id: c for c in cues}
    win_cues = [by_id[i] for i in win.cue_ids]
    lines = [
        f"窗口时间：{fmt_hmsms(win.start)} – {fmt_hmsms(win.end)}",
        f"合法 ID 范围：{win.cue_ids[0]} ~ {win.cue_ids[-1]}（只能使用下面列出的 ID）",
        "",
        "字幕：",
    ]
    for cue in win_cues:
        lines.append(f"[{cue.id}] {fmt_hmsms(cue.start)}–{fmt_hmsms(cue.end)} | {cue.top}")
    return lines, win_cues


def build_prompt(win: Window, cues: list[Cue], cfg: dict[str, Any]) -> str:
    lines, win_cues = _window_header(win, cues)
    span = win.end - win.start
    avg_cue = span / len(win_cues) if win_cues else 0
    min_cues = max(1, math.ceil(cfg["min_clip_ms"] / avg_cue)) if avg_cue else 1
    max_cues = max(1, math.floor(cfg["max_clip_ms"] / avg_cue)) if avg_cue else len(win_cues)
    lines += [
        "",
        f"本窗口共 {len(win_cues)} 条字幕，平均每条约 {avg_cue / 1000:.1f} 秒；"
        f"{cfg['min_clip_ms'] // 1000}–{cfg['max_clip_ms'] // 1000} 秒大约相当于 "
        f"{min_cues}–{max_cues} 条字幕。",
        "请选出一个能独立成片、只讲清一个论点的小片段（约 1 分钟），",
        "而不是大而全的长论证。按顺序判断：",
        "",
        "1. 独立成句：start 必须是完整主谓句的开头，不能是半句、承接词或从句开头",
        "（brought / which / that / because / but also 之类一律不要）。",
        "2. 论点单一：整段只回答一个问题；出现第二个独立论点时，在它之前收尾。",
        "3. 结论完整：end 必须在论点收束之后；不要停在半句、反问、例子中间。",
        "4. 信息密度：至少有一个具体数据、机制或案例，不要只选金句或情绪化片段。",
        "5. 可追溯：start/end 只能使用上面列出的字幕 ID，时间以字幕为准。",
        "",
        f"时长：{cfg['prefer_min_ms'] // 1000}–{cfg['prefer_max_ms'] // 1000} 秒最佳；"
        f"低于 {cfg['min_clip_ms'] // 1000} 秒或超过 {cfg['max_clip_ms'] // 1000} 秒无效。"
        "一集最终会保留 3–5 条这样彼此独立的小论点。",
        "",
        "边界示例（只看边界，不要照抄内容）：",
        "- 反例 start：「…and I'm like well no because like…」（半句 + 承接词）",
        "- 正例 start：「…so just give us a high level TLDR why is CPU now bottleneck…？」"
        "（完整问题）",
        "- 反例 end：「…and that's why…」（话没说完）",
        "- 正例 end：「…so that's the constraint we run into.」（结论句）",
        "- 不选：广告、寒暄、纯过渡、重复口误、没有结论的闲聊。",
        "",
        "优先级：独立完整的问题—解释—结论 > 单条金句。",
        "",
        "只输出一个 JSON 对象，不要代码块、不要解释，字段固定：",
        '{"start_cue_id": <整数>, "end_cue_id": <整数>, '
        '"title": "<不超过 20 字的简体中文标题>", '
        '"summary": "<一句话简体中文摘要，写清问题与结论>"}',
    ]
    return "\n".join(lines)


def build_extend_prompt(win: Window, cues: list[Cue], record: dict[str, Any],
                       cfg: dict[str, Any]) -> str:
    """One correction call: ask for a later end when the model picked < min_clip_ms."""
    lines, _ = _window_header(win, cues)
    seconds = record["duration_ms"] / 1000
    lines += [
        "",
        f"你选取的 {record['start_cue_id']} ~ {record['end_cue_id']} 实测只有 "
        f"{seconds:.1f} 秒，讨论尚未充分展开。",
        "请将结束边界向后延伸，直到该论点推导完毕，使总时长落在 "
        f"{cfg['prefer_min_ms'] // 1000}–{cfg['prefer_max_ms'] // 1000} 秒之间。",
        f"start_cue_id 保持 {record['start_cue_id']} 不变；end_cue_id 必须大于 "
        f"{record['end_cue_id']}，且只能使用上面列出的 ID。",
        "",
        "只输出一个 JSON 对象，不要代码块、不要解释：",
        '{"end_cue_id": <整数>}',
    ]
    return "\n".join(lines)


def _llm_headers() -> dict[str, str]:
    key = os.environ.get("LLM_API_KEY", "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def build_start_prompt(win: "Window", cues: list[Cue], record: dict[str, Any],
                       cfg: dict[str, Any]) -> str:
    """One correction call: the model's start is mid-sentence, pick a clean one."""
    lines, _ = _window_header(win, cues)
    start_cue = next((c for c in cues if c.id == record["start_cue_id"]), None)
    opening = start_cue.top.strip()[:120] if start_cue else ""
    lines += [
        "",
        f"你选取的起点第 {record['start_cue_id']} 条字幕是半句或承接词开头：",
        f"「{opening}」",
        "",
        "请重新给出一组 start_cue_id / end_cue_id：",
        "1. start 必须是独立完整主谓句的开头，不能是 And / But / Because / Which / That /",
        "   Also / However / Yeah / Um / I mean 等承接或垫话开头，也不能是半句。",
        "2. end 必须是句末（句号 / 问号 / 感叹号）。",
        f"3. 总时长 {cfg['prefer_min_ms'] // 1000}–{cfg['prefer_max_ms'] // 1000} 秒，"
        f"不得低于 {cfg['min_clip_ms'] // 1000} 秒或超过 {cfg['max_clip_ms'] // 1000} 秒。",
        "4. start/end 只能使用上面列出的字幕 ID，且 start < end。",
        "",
        "只输出一个 JSON 对象，不要代码块、不要解释：",
        '{"start_cue_id": <整数>, "end_cue_id": <整数>}',
    ]
    return "\n".join(lines)


def discover_model(base: str, timeout: int = 30) -> str:
    r = requests.get(f"{base}/v1/models", timeout=timeout, headers=_llm_headers())
    r.raise_for_status()
    return r.json()["data"][0]["id"]


def extract_json_object(text: str) -> dict[str, Any]:
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


def call_model(base: str, model: str, prompt: str, win: Window,
               cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": 500,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    attempts: list[dict[str, Any]] = []
    valid_ids = set(win.cue_ids)
    for attempt in range(1, cfg["model_retries"] + 2):
        record: dict[str, Any] = {"attempt": attempt}
        try:
            resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                 timeout=(10, cfg["model_timeout_s"]),
                                 headers=_llm_headers())
            if resp.status_code == 400 and "response_format" in payload:
                # server without json_object support: degrade once, deterministically
                payload.pop("response_format")
                resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                     timeout=(10, cfg["model_timeout_s"]),
                                     headers=_llm_headers())
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            record["raw"] = content
            obj = extract_json_object(content)
            missing = [k for k in ("start_cue_id", "end_cue_id", "title", "summary")
                       if k not in obj]
            if missing:
                raise ValueError(f"missing fields: {missing}")
            start_id, end_id = obj["start_cue_id"], obj["end_cue_id"]
            for key, value in (("start_cue_id", start_id), ("end_cue_id", end_id)):
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError(f"{key} is not an integer: {value!r}")
            if start_id not in valid_ids or end_id not in valid_ids:
                raise ValueError(f"ID out of window {win.cue_ids[0]}~{win.cue_ids[-1]}: "
                                 f"{start_id}, {end_id}")
            if end_id < start_id:
                raise ValueError(f"end_cue_id {end_id} < start_cue_id {start_id}")
            title = str(obj["title"]).strip()
            summary = str(obj["summary"]).strip()
            if not title or not summary:
                raise ValueError("empty title/summary")
            record["ok"] = True
            attempts.append(record)
            return {"start_cue_id": start_id, "end_cue_id": end_id,
                    "title": title, "summary": summary}, attempts
        except Exception as exc:  # transport / parse / validation
            record["ok"] = False
            record["error"] = str(exc)
            attempts.append(record)
            RUN.log(f"window {win.index} attempt {attempt} failed: {exc}")
            if attempt <= cfg["model_retries"]:
                time.sleep(1)
    return None, attempts


def _candidate_record(*, candidate: dict[str, Any], start_id: int, end_id: int,
                      win: Window, by_id: dict[int, Cue]) -> dict[str, Any]:
    start_cue, end_cue = by_id[start_id], by_id[end_id]
    b_score, b_notes = boundary_score(start_cue, end_cue, by_id.get(start_id - 1))
    return {
        "source_window": win.index,
        "start_cue_id": start_id,
        "end_cue_id": end_id,
        "title": candidate["title"],
        "summary": candidate["summary"],
        "start_ms": start_cue.start,
        "end_ms": end_cue.end,
        "duration_ms": end_cue.end - start_cue.start,
        "boundary_score": b_score,
        "boundary_notes": b_notes,
    }


def call_start_model(base: str, model: str, prompt: str, win: "Window",
                     by_id: dict[int, Cue], cfg: dict[str, Any]
                     ) -> tuple[tuple[int, int] | None, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": 80,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    record: dict[str, Any] = {"attempt": 1}
    try:
        resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                             timeout=(10, cfg["model_timeout_s"]),
                             headers=_llm_headers())
        if resp.status_code == 400 and "response_format" in payload:
            payload.pop("response_format")
            resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                 timeout=(10, cfg["model_timeout_s"]),
                                 headers=_llm_headers())
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        record["raw"] = content
        obj = extract_json_object(content)
        start_id, end_id = obj.get("start_cue_id"), obj.get("end_cue_id")
        for value in (start_id, end_id):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"cue id is not an integer: {value!r}")
        if start_id not in set(win.cue_ids) or end_id not in set(win.cue_ids):
            raise ValueError("cue id out of window")
        if start_id >= end_id:
            raise ValueError("start_cue_id must be smaller than end_cue_id")
        text = by_id[start_id].top.strip()
        if DEPENDENT_START.match(text) or FILLER_START.match(text):
            raise ValueError(f"repaired start is still a bad opener: {text[:40]}")
        duration = by_id[end_id].end - by_id[start_id].start
        if not (cfg["min_clip_ms"] <= duration <= cfg["max_clip_ms"]):
            raise ValueError(f"repaired duration {duration} ms out of range")
        record["ok"] = True
        return (start_id, end_id), record
    except Exception as exc:
        record["ok"] = False
        record["error"] = str(exc)
        RUN.log(f"window {win.index} start repair failed: {exc}")
        return None, record


def call_extend_model(base: str, model: str, prompt: str, win: Window,
                      start_id: int, cfg: dict[str, Any]
                      ) -> tuple[int | None, list[dict[str, Any]]]:
    """One correction request: return a later end cue, or None.

    Only called when the first candidate is shorter than min_clip_ms and
    its boundary is not a hard reject.  Never loops (the caller allows one).
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": 80,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    record: dict[str, Any] = {"attempt": 1}
    try:
        resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                             timeout=(10, cfg["model_timeout_s"]),
                             headers=_llm_headers())
        if resp.status_code == 400 and "response_format" in payload:
            payload.pop("response_format")
            resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                 timeout=(10, cfg["model_timeout_s"]),
                                 headers=_llm_headers())
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        record["raw"] = content
        obj = extract_json_object(content)
        end_id = obj.get("end_cue_id")
        if isinstance(end_id, bool) or not isinstance(end_id, int):
            raise ValueError(f"end_cue_id is not an integer: {end_id!r}")
        if end_id not in set(win.cue_ids):
            raise ValueError(f"end_cue_id out of window: {end_id}")
        if end_id <= start_id:
            raise ValueError(f"end_cue_id {end_id} <= start {start_id}")
        record["ok"] = True
        return end_id, [record]
    except Exception as exc:
        record["ok"] = False
        record["error"] = str(exc)
        RUN.log(f"window {win.index} extend failed: {exc}")
        return None, [record]


def build_title_prompt(*, win: Window, cues: list[Cue], record: dict[str, Any],
                       existing_titles: list[str], cfg: dict[str, Any]) -> str:
    """Ask for a title that is explicitly different from the already-picked ones."""
    lines, _ = _window_header(win, cues)
    lines += [
        "",
        f"候选片段：{record['start_cue_id']} ~ {record['end_cue_id']}",
        f"候选摘要：{record['summary']}",
        f"已有标题：{'；'.join(existing_titles) if existing_titles else '无'}",
        "请为这个候选生成一个与已有标题明显不同的中文标题，突出它与其它候选"
        "不同的核心矛盾，不超过 20 个字，不要营销词。",
        '只输出 JSON：{"title": "<标题>"}',
    ]
    return "\n".join(lines)


def call_title_model(base: str, model: str, prompt: str,
                     cfg: dict[str, Any]) -> str | None:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": 80,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                             timeout=(10, cfg["model_timeout_s"]),
                             headers=_llm_headers())
        if resp.status_code == 400 and "response_format" in payload:
            payload.pop("response_format")
            resp = requests.post(f"{base}/v1/chat/completions", json=payload,
                                 timeout=(10, cfg["model_timeout_s"]),
                                 headers=_llm_headers())
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        title = str(extract_json_object(content).get("title", "")).strip()
        if not title or len(title) > 20:
            raise ValueError(f"invalid title: {title!r}")
        return title
    except Exception as exc:
        RUN.log(f"title repair failed: {exc}")
        return None


def ensure_unique_titles(selected: list[dict[str, Any]],
                         window_results: list[dict[str, Any]],
                         cues: list[Cue], by_id: dict[int, Cue],
                         cfg: dict[str, Any]) -> None:
    if not selected:
        return
    window_by_index = {w["index"]: w for w in window_results}
    used: set[str] = set()
    for cand in selected:
        if cand["title"] in used:
            data = window_by_index.get(cand["source_window"])
            win = Window(index=data["index"], start=data["start_ms"],
                         end=data["end_ms"], cue_ids=data["cue_ids"])
            prompt = build_title_prompt(win=win, cues=cues, record=cand,
                                        existing_titles=sorted(used), cfg=cfg)
            new_title = call_title_model(cfg["base_url"], cfg["model"], prompt, cfg)
            if not new_title or new_title in used:
                fallback = (cand.get("summary") or "").split("，")[0][:20]
                fallback = fallback.strip("。；，, ")
                if not fallback or fallback in used:
                    fallback = f"{cand['title']}（{cand['start_cue_id']}）"[:20]
                new_title = fallback
            RUN.log(f"title repair: {cand['title']} -> {new_title}")
            cand["title"] = new_title
        used.add(cand["title"])


def analyze(cues: list[Cue], cfg: dict[str, Any], video_id: str,
            work_dir: Path | None = None) -> dict[str, Any]:
    windows = build_windows(cues, cfg["window_ms"], cfg["overlap_ms"], cfg["min_clip_ms"])
    RUN.log(f"windows: {len(windows)}")

    model: str | None = cfg.get("model")
    model_error: str | None = None
    if not model:
        try:
            model = discover_model(cfg["base_url"])
            cfg["model"] = model
            RUN.log(f"model: {model}")
        except Exception as exc:
            model_error = f"model discovery failed: {exc}"
            RUN.log(model_error)

    by_id = {c.id: c for c in cues}
    window_results: list[dict[str, Any]] = []
    candidates_raw: list[dict[str, Any]] = []
    start_rejects: list[dict[str, Any]] = []

    for win in windows:
        prompt = build_prompt(win, cues, cfg)
        if work_dir is not None:
            (work_dir / f"window-{win.index:02d}.prompt.txt").write_text(prompt, encoding="utf-8")
        entry: dict[str, Any] = {
            "index": win.index, "start_ms": win.start, "end_ms": win.end,
            "min_id": win.cue_ids[0], "max_id": win.cue_ids[-1],
            "cue_count": len(win.cue_ids), "cue_ids": win.cue_ids,
        }
        if model_error or not model:
            entry.update(status="FAILED", attempts=[], candidate=None,
                         error=model_error or "no model")
        else:
            candidate, attempts = call_model(cfg["base_url"], model, prompt, win, cfg)
            entry["attempts"] = attempts
            if candidate is None:
                entry.update(status="FAILED", candidate=None,
                             error=attempts[-1].get("error") if attempts else "unknown")
            else:
                record = _candidate_record(
                    candidate=candidate, start_id=candidate["start_cue_id"],
                    end_id=candidate["end_cue_id"], win=win, by_id=by_id)
                record, snap_reject = snap_start(record, by_id, win, cfg)
                if record is None:
                    repair_prompt = build_start_prompt(win, cues, {
                        "start_cue_id": candidate["start_cue_id"],
                        "end_cue_id": candidate["end_cue_id"]}, cfg)
                    if work_dir is not None:
                        (work_dir / f"window-{win.index:02d}.start.prompt.txt").write_text(
                            repair_prompt, encoding="utf-8")
                    pair, repair_attempt = call_start_model(
                        cfg["base_url"], model, repair_prompt, win, by_id, cfg)
                    entry["start_repair"] = repair_attempt
                    if pair is not None:
                        start_id, end_id = pair
                        record = _candidate_record(
                            candidate=candidate, start_id=start_id,
                            end_id=end_id, win=win, by_id=by_id)
                        record["start_repaired_from"] = {
                            "start_cue_id": candidate["start_cue_id"],
                            "stage": snap_reject["stage"]}
                        RUN.log(f"window {win.index}: repaired start cue "
                                f"{start_id} ({record['duration_ms'] / 1000:.1f}s)")
                    else:
                        start_rejects.append({
                            "candidate": {"source_window": win.index,
                                          "start_cue_id": candidate["start_cue_id"],
                                          "end_cue_id": candidate["end_cue_id"],
                                          "title": candidate["title"]},
                            "stage": snap_reject["stage"],
                            "reason": snap_reject["reason"],
                        })
                        entry.update(status="OK", candidate=None, rejected=snap_reject)
                if record is not None and record["duration_ms"] > cfg["prefer_max_ms"]:
                    clamped = clamp_end(record["start_cue_id"], record["end_cue_id"],
                                        by_id, cfg)
                    if clamped is not None and clamped != record["end_cue_id"]:
                        clamped_from = {"end_cue_id": record["end_cue_id"],
                                        "duration_ms": record["duration_ms"]}
                        new_record = _candidate_record(
                            candidate=candidate, start_id=record["start_cue_id"],
                            end_id=clamped, win=win, by_id=by_id)
                        if "start_snapped_from" in record:
                            new_record["start_snapped_from"] = record["start_snapped_from"]
                        _carry_trim(new_record, record)
                        new_record["clamped_from"] = clamped_from
                        new_record["soft_cut"] = not TERMINAL_END.search(
                            by_id[clamped].top.strip())
                        record = new_record
                        RUN.log(f"window {win.index}: clamped end cue {clamped} "
                                f"({record['duration_ms'] / 1000:.1f}s)")
                extended = False
                if (record is not None
                        and record["duration_ms"] < cfg["min_clip_ms"]
                        and "hard_reject" not in record["boundary_notes"]):
                    ext_prompt = build_extend_prompt(win, cues, record, cfg)
                    if work_dir is not None:
                        (work_dir / f"window-{win.index:02d}.extend.prompt.txt").write_text(
                            ext_prompt, encoding="utf-8")
                    new_end, ext_attempts = call_extend_model(
                        cfg["base_url"], model, ext_prompt, win,
                        record["start_cue_id"], cfg)
                    entry["extend_attempts"] = ext_attempts
                    if work_dir is not None:
                        (work_dir / f"window-{win.index:02d}.extend.response.json"
                         ).write_text(json.dumps({"attempts": ext_attempts},
                                                 ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")
                    if new_end is not None and new_end != record["end_cue_id"]:
                        extended_record = _candidate_record(
                            candidate=candidate, start_id=record["start_cue_id"],
                            end_id=new_end, win=win, by_id=by_id)
                        extended_record["extended_from"] = {
                            "end_cue_id": record["end_cue_id"],
                            "duration_ms": record["duration_ms"],
                        }
                        _carry_trim(extended_record, record)
                        record = extended_record
                        extended = True
                        RUN.log(f"window {win.index}: extended end cue "
                                f"{new_end} ({record['duration_ms'] / 1000:.1f}s)")
                        if record["duration_ms"] > cfg["prefer_max_ms"]:
                            clamped = clamp_end(
                                record["start_cue_id"], record["end_cue_id"], by_id, cfg)
                            if clamped is not None and clamped != record["end_cue_id"]:
                                clamped_from = {
                                    "end_cue_id": record["end_cue_id"],
                                    "duration_ms": record["duration_ms"],
                                }
                                previous = record
                                record = _candidate_record(
                                    candidate=candidate,
                                    start_id=record["start_cue_id"],
                                    end_id=clamped, win=win, by_id=by_id)
                                record["extended_from"] = extended_record["extended_from"]
                                record["soft_clamped_from"] = clamped_from
                                _carry_trim(record, previous)
                                RUN.log(f"window {win.index}: soft-clamped end cue "
                                        f"{clamped} ({record['duration_ms'] / 1000:.1f}s)")
                if record is not None:
                    entry.update(status="OK", extended=extended,
                                 soft_clamped="soft_clamped_from" in record,
                                 clamped="clamped_from" in record,
                                 start_snapped=("start_snapped_from" in record
                                                or "start_repaired_from" in record),
                                 candidate={"start_cue_id": record["start_cue_id"],
                                            "end_cue_id": record["end_cue_id"],
                                            "title": record["title"],
                                            "summary": record["summary"]})
                    candidates_raw.append(record)
        if work_dir is not None:
            (work_dir / f"window-{win.index:02d}.response.json").write_text(
                json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        RUN.log(f"window {win.index}: {entry['status']} "
                f"({win.cue_ids[0]}~{win.cue_ids[-1]}, {len(win.cue_ids)} cues)")
        window_results.append(entry)

    valid, removed = filter_candidates(candidates_raw, window_results, by_id, cfg)
    removed.extend(start_rejects)
    selected = select_with_budget(valid, cfg)
    if len(selected) > 1:
        ensure_unique_titles(selected, window_results, cues, by_id, cfg)
    for cand in valid[len(selected):]:
        removed.append({"candidate": cand, "stage": "quota",
                        "reason": f"outside the {cfg['reel_budget_ms']} ms reel budget "
                                  f"or the {cfg['max_clips']}-clip cap"})
    RUN.log(f"selection: {len(selected)} clip(s), reel budget "
            f"{sum(c['duration_ms'] for c in selected) / 1000:.1f}s clips + "
            f"{cfg.get('intro_budget_ms', 0) / 1000:.1f}s intro")

    window_failures = sum(1 for w in window_results if w["status"] != "OK")
    if not window_results:
        analysis_status = "ANALYSIS_FAILED"
    elif window_failures == len(window_results):
        analysis_status = "ANALYSIS_FAILED"
    elif window_failures:
        analysis_status = "ANALYSIS_PARTIAL"
    elif not valid:
        analysis_status = "NO_CANDIDATES"
    else:
        analysis_status = "ANALYSIS_OK"

    return {
        "schema_version": SCHEMA_VERSION,
        "video_id": video_id,
        "srt": rel(cfg["srt_path"]),
        "generated_at": now_iso(),
        "config": {k: v for k, v in cfg.items()
                   if k not in ("srt_path", "video_path", "out_dir")},
        "cue_count": len(cues),
        "source_span_ms": cues[-1].end - cues[0].start,
        "analysis_status": analysis_status,
        "analysis_complete": window_failures == 0,
        "model": model,
        "windows": window_results,
        "candidates_raw": candidates_raw,
        "candidates_valid": valid,
        "candidates_selected": selected,
        "candidates_removed": removed,
        "errors": [model_error] if model_error else [],
    }


# --------------------------------------------------------------------------
# module 4: deterministic filtering, dedupe, quota
# --------------------------------------------------------------------------
def overlap_ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
    overlap = min(a["end_ms"], b["end_ms"]) - max(a["start_ms"], b["start_ms"])
    if overlap <= 0:
        return 0.0
    return overlap / min(a["duration_ms"], b["duration_ms"])


def boundary_score(start: Cue, end: Cue,
                   prev: Cue | None = None) -> tuple[int, list[str]]:
    """Score the start/end boundary of a candidate (-2..5, higher is better).

    Only ``filler_start`` + ``non_terminal_end`` + ``continuation_end`` is a
    hard reject; every other imperfection is just a ranking penalty because
    automatic captions routinely split sentences across cues.
    """
    score = 0
    notes: list[str] = []
    start_text = start.top.strip()
    end_text = end.top.strip()

    if DEPENDENT_START.match(start_text):
        score -= 2
        notes.append("dependent_start")
    elif FILLER_START.match(start_text):
        score -= 2
        notes.append("filler_start")
    else:
        score += 2
        notes.append("clean_start")

    if "?" in start_text or (prev is not None and "?" in prev.top):
        score += 1
        notes.append("question_boundary")

    if TERMINAL_END.search(end_text):
        score += 2
        notes.append("terminal_end")
    else:
        notes.append("non_terminal_end")
        if CONTINUATION_END.search(end_text):
            score -= 2
            notes.append("continuation_end")

    has_bad_start = "filler_start" in notes
    has_bad_end = ("non_terminal_end" in notes and "continuation_end" in notes)
    if has_bad_start and has_bad_end:
        score = min(score, -1)
        notes.append("hard_reject")

    return max(score, -2), notes


def overlap_ms(a: dict[str, Any], b: dict[str, Any]) -> int:
    overlap = min(a["end_ms"], b["end_ms"]) - max(a["start_ms"], b["start_ms"])
    return max(0, overlap)


def soft_clamp_end(start_id: int, end_id: int, by_id: dict[int, Cue],
                   cfg: dict[str, Any]) -> int | None:
    """Walk back to the nearest terminal cue that fits <= prefer_max_ms.

    Returns None when no terminal cue fits (then the original extension is
    kept, still bounded by the 10-minute hard gate).
    """
    start_ms = by_id[start_id].start
    for cue_id in range(end_id, start_id, -1):
        cue = by_id[cue_id]
        duration = cue.end - start_ms
        if duration > cfg["prefer_max_ms"]:
            continue
        if duration < cfg["min_clip_ms"]:
            break
        if TERMINAL_END.search(cue.top.strip()):
            return cue_id
    return None


def strip_filler_prefix(text: str) -> tuple[str | None, str]:
    """Return (prefix, rest), stripping repeated fillers ("Yeah I mean ...")."""
    rest = text.strip()
    consumed: list[str] = []
    while rest:
        lowered = rest.lower()
        match = None
        for prefix in FILLER_PREFIXES:
            if not lowered.startswith(prefix):
                continue
            end = len(prefix)
            if end < len(rest) and rest[end].isalpha():
                continue
            match = prefix
            break
        if match is None:
            break
        candidate = rest[len(match):].lstrip(" ,.،、")
        if len(candidate.split()) < 4 and len(candidate) < 8:
            break
        consumed.append(rest[:len(match)])
        rest = candidate
    if not consumed:
        return None, text.strip()
    return " ".join(consumed), rest


def estimate_prefix_ms(prefix: str) -> int:
    """Rough spoken length of a filler: ~400 ms per word, clamped 300-1200 ms."""
    words = max(1, len(prefix.split()))
    return min(1200, max(300, 400 * words))


_ZH_FILLER_HEAD = re.compile(r"^(?:是的|对|嗯|呃|那个|我的意思是|所以|然后|就是说|好)[，,、。\s]*")


def _strip_zh_filler(text: str) -> str:
    """Drop the Chinese translation of a trimmed filler at the head of a cue."""
    previous = None
    while previous != text:
        previous = text
        text = _ZH_FILLER_HEAD.sub("", text, count=1)
    return text or previous


def _strip_prefix_from_text(text: str, prefix: str) -> str:
    if prefix and text.lower().startswith(prefix.lower()):
        return text[len(prefix):].lstrip(" ,.،、")
    return text


def _looks_mid_sentence(cue: Cue, prev: Cue | None) -> bool:
    """Lowercase opener after a cue that did not end a sentence = mid-sentence."""
    text = cue.top.strip()
    return bool(text) and text[0].islower() and prev is not None and         not TERMINAL_END.search(prev.top.strip())


def _sentence_start(cue: Cue, prev: Cue | None) -> bool:
    """A cue may open a clip only when it is not a filler and starts a sentence."""
    text = cue.top.strip()
    if not text or DEPENDENT_START.match(text) or FILLER_START.match(text):
        return False
    return prev is None or bool(TERMINAL_END.search(prev.top.strip()))


def _carry_trim(new_record: dict[str, Any], old_record: dict[str, Any]) -> dict[str, Any]:
    """Copy prefix-trim metadata onto a rebuilt record and shorten its duration."""
    trim = int(old_record.get("trim_start_ms") or 0)
    if trim:
        new_record["trim_start_ms"] = trim
        new_record["trim_prefix"] = old_record.get("trim_prefix", "")
        new_record["trimmed_text"] = old_record.get("trimmed_text", "")
        new_record["duration_ms"] = max(1, int(new_record["duration_ms"]) - trim)
    return new_record


def snap_start(record: dict[str, Any], by_id: dict[int, Cue], win: "Window",
               cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Reject clause openers and repair filler openers by moving the start forward.

    The repair stays inside the producing window and within 30 s of the model's
    original start, so the candidate still covers the argument the model chose.
    """
    start_id = record["start_cue_id"]
    text = by_id[start_id].top.strip()

    prefix, rest = strip_filler_prefix(text)
    if prefix:
        trim_ms = estimate_prefix_ms(prefix)
        duration = record["end_ms"] - (record["start_ms"] + trim_ms)
        if not DEPENDENT_START.match(rest) and duration >= cfg["min_clip_ms"]:
            trimmed = dict(record)
            trimmed["trim_start_ms"] = trim_ms
            trimmed["trim_prefix"] = prefix
            trimmed["trimmed_text"] = rest
            trimmed["duration_ms"] = duration
            trimmed["boundary_notes"] = list(record.get("boundary_notes", [])) + [
                "filler_prefix_trimmed"]
            return trimmed, None
        if DEPENDENT_START.match(rest):
            return None, {"stage": "dependent_start",
                          "reason": f"clip opens with a clause connector: {rest[:48]}"}

    kind = ("dependent" if DEPENDENT_START.match(text)
            else "filler" if FILLER_START.match(text) else None)
    if kind is None:
        if not _looks_mid_sentence(by_id[start_id], by_id.get(start_id - 1)):
            return record, None
        kind = "mid_sentence"

    limit_ms = int(record["start_ms"]) + 30_000
    for cue_id in win.cue_ids:
        if cue_id <= start_id:
            continue
        cue = by_id.get(cue_id)
        if cue is None or cue.start > limit_ms:
            break
        landing = cue.top.strip()
        if DEPENDENT_START.match(landing):
            continue
        landing_prefix, landing_rest = strip_filler_prefix(landing)
        if landing_prefix:
            pass                      # filler head is fine: it gets trimmed below
        elif not _sentence_start(cue, by_id.get(cue_id - 1)):
            continue
        end_id = record["end_cue_id"] if record["end_cue_id"] >= cue_id else None
        if end_id is not None:
            duration = by_id[end_id].end - cue.start
        else:
            duration = -1
        if end_id is None or not (cfg["min_clip_ms"] <= duration <= cfg["max_clip_ms"]):
            end_id = clamp_end(cue_id, win.cue_ids[-1], by_id, cfg)
            if end_id is None:
                continue
            duration = by_id[end_id].end - cue.start
            if not (cfg["min_clip_ms"] <= duration <= cfg["max_clip_ms"]):
                continue
        snapped = dict(record)
        snapped["start_snapped_from"] = {"start_cue_id": start_id,
                                         "start_ms": record["start_ms"],
                                         "kind": kind}
        snapped["start_cue_id"] = cue_id
        snapped["end_cue_id"] = end_id
        snapped["start_ms"] = cue.start
        snapped["end_ms"] = by_id[end_id].end
        snapped["duration_ms"] = duration
        if landing_prefix:
            trim_ms = estimate_prefix_ms(landing_prefix)
            if duration - trim_ms < cfg["min_clip_ms"]:
                continue
            snapped["trim_start_ms"] = trim_ms
            snapped["trim_prefix"] = landing_prefix
            snapped["trimmed_text"] = landing_rest
            snapped["duration_ms"] = duration - trim_ms
        score, notes = boundary_score(cue, by_id[end_id], by_id.get(cue_id - 1))
        snapped["boundary_score"] = score
        snapped["boundary_notes"] = notes
        return snapped, None
    reason = (f"clip opens with a clause connector: {text[:48]}" if kind == "dependent"
              else "no clean sentence start within 30 s of the model's pick")
    stage = {"dependent": "dependent_start", "filler": "filler_start",
             "mid_sentence": "mid_sentence_start"}.get(kind, "filler_start")
    return None, {"stage": stage, "reason": reason}


def clamp_end(start_id: int, end_id: int, by_id: dict[int, Cue],
              cfg: dict[str, Any]) -> int | None:
    """Walk back to a terminal cue: prefer 50-70 s, fall back to <= max_clip_ms."""
    start_ms = by_id[start_id].start
    fallback: int | None = None
    soft: int | None = None
    for cue_id in range(end_id, start_id - 1, -1):
        cue = by_id.get(cue_id)
        if cue is None:
            continue
        duration = cue.end - start_ms
        if duration < cfg["min_clip_ms"]:
            break
        if TERMINAL_END.search(cue.top.strip()):
            if cfg["prefer_min_ms"] <= duration <= cfg["prefer_max_ms"]:
                return cue_id
            if fallback is None and duration <= cfg["max_clip_ms"]:
                fallback = cue_id
        elif soft is None and cfg["prefer_min_ms"] <= duration <= cfg["prefer_max_ms"]:
            soft = cue_id
    return fallback if fallback is not None else soft


def rank_key(cand: dict[str, Any], cfg: dict[str, Any],
             kept: tuple[dict[str, Any], ...] = ()) -> tuple:
    dur = cand["duration_ms"]
    in_prefer = 0 if cfg["prefer_min_ms"] <= dur <= cfg["prefer_max_ms"] else 1
    midpoint = (cfg["prefer_min_ms"] + cfg["prefer_max_ms"]) // 2
    penalty = sum(1 for prev in kept
                  if overlap_ms(cand, prev) > int(cfg.get("overlap_penalty_ms", 30_000)))
    return (penalty, in_prefer, -int(cand.get("boundary_score", 0)),
            abs(dur - midpoint), cand["start_ms"], cand["start_cue_id"])


def select_with_budget(valid: list[dict[str, Any]],
                       cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Greedy pick by rank until the reel budget (intro + clips + transitions) is full."""
    cap = int(cfg["max_clips"])
    budget = int(cfg.get("reel_budget_ms") or 0)
    if budget <= 0:
        return valid[:cap]
    total = int(cfg.get("intro_budget_ms") or 0)
    transition = int(cfg.get("transition_ms") or 0)
    picked: list[dict[str, Any]] = []
    for cand in valid:
        if len(picked) >= cap:
            break
        nxt = total + int(cand["duration_ms"]) + (transition if picked else 0)
        if nxt > budget:
            break
        picked.append(cand)
        total = nxt
    return picked


def filter_candidates(candidates: list[dict[str, Any]], windows: list[dict[str, Any]],
                      by_id: dict[int, Cue], cfg: dict[str, Any]
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    removed: list[dict[str, Any]] = []
    window_ids = {w["index"]: set(w["cue_ids"]) for w in windows}
    survivors: list[dict[str, Any]] = []

    for cand in candidates:
        ids = window_ids.get(cand["source_window"], set())
        if cand["start_cue_id"] not in ids or cand["end_cue_id"] not in ids:
            removed.append({"candidate": cand, "stage": "ownership",
                            "reason": "cue ID not in producing window"})
            continue
        start_cue = by_id[cand["start_cue_id"]]
        end_cue = by_id[cand["end_cue_id"]]
        if start_cue.start != cand["start_ms"] or end_cue.end != cand["end_ms"]:
            removed.append({"candidate": cand, "stage": "ownership",
                            "reason": "candidate times do not match cue timestamps"})
            continue
        if "boundary_score" not in cand:
            b_score, b_notes = boundary_score(
                start_cue, end_cue, by_id.get(start_cue.id - 1))
            cand["boundary_score"] = b_score
            cand["boundary_notes"] = b_notes
        if "hard_reject" in cand.get("boundary_notes", []):
            removed.append({
                "candidate": cand, "stage": "boundary",
                "reason": "filler_start + non_terminal_end + continuation_end",
            })
            continue
        dur = cand["duration_ms"]
        if not (cfg["min_clip_ms"] <= dur <= cfg["max_clip_ms"]):
            removed.append({
                "candidate": cand, "stage": "duration",
                "reason": f"{dur} ms outside [{cfg['min_clip_ms']}, {cfg['max_clip_ms']}]",
            })
            continue
        survivors.append(cand)

    remaining = list(survivors)
    kept: list[dict[str, Any]] = []
    while remaining:
        remaining.sort(key=lambda c: rank_key(c, cfg, tuple(kept)))
        cand = remaining.pop(0)
        duplicate = None
        for prev in kept:
            ratio = overlap_ratio(cand, prev)
            if ratio > cfg["dup_overlap_ratio"]:
                duplicate = (prev, ratio)
                break
        if duplicate:
            prev, ratio = duplicate
            removed.append({
                "candidate": cand, "stage": "duplicate",
                "reason": f"overlap ratio {ratio:.2f} > {cfg['dup_overlap_ratio']} "
                          f"with window {prev['source_window']} candidate",
                "duplicate_of": {
                    "source_window": prev["source_window"],
                    "start_cue_id": prev["start_cue_id"],
                    "end_cue_id": prev["end_cue_id"],
                },
            })
        else:
            kept.append(cand)

    return kept, removed


# --------------------------------------------------------------------------
# module 5: subtitle clamping + render
# --------------------------------------------------------------------------
def clamp_cues(cues: list[Cue], clip_start: int, length: int
               ) -> list[tuple[int, int, str, str]]:
    rows: list[tuple[int, int, str, str]] = []
    for cue in cues:
        if cue.end <= clip_start or cue.start >= clip_start + length:
            continue
        new_start = max(0, cue.start - clip_start)
        new_end = min(length, cue.end - clip_start)
        if new_start < new_end:
            rows.append((new_start, new_end, cue.top, cue.bottom))
    return rows


def escape_filter_path(path: Path) -> str:
    """Use a ROOT-relative POSIX path when possible, else escape a Windows path."""
    resolved = path.resolve()
    try:
        text = resolved.relative_to(ROOT).as_posix()
    except ValueError:
        text = resolved.as_posix()
    text = text.replace("\\", "/")
    for ch in "':,[];":
        text = text.replace(ch, "\\" + ch)
    return text


def probe_source(video: Path) -> dict[str, Any]:
    proc = run_cmd([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(video),
    ], timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video_stream is None or audio_stream is None:
        raise RuntimeError("source has no video+audio stream")
    fps = video_stream.get("r_frame_rate", "0/0")
    avg = video_stream.get("avg_frame_rate", fps)
    vfr = fps != avg
    return {
        "duration_ms": int(round(float(data["format"]["duration"]) * 1000)),
        "fps": fps,
        "avg_fps": avg,
        "vfr": vfr,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
    }


def render_clip(video: Path, clip: dict[str, Any], rows: list[tuple[int, int, str, str]],
                cfg: dict[str, Any], work_dir: Path, index: int,
                source_info: dict[str, Any],
                dub: Path | None = None) -> tuple[Path, Path, list[str]]:
    stem = f"clip-{index:02d}"
    srt_path = work_dir / f"{stem}.srt"
    ass_path = work_dir / f"{stem}.ass"
    tmp_path = work_dir / f"{stem}.tmp.mp4"
    ffmpeg_log = work_dir / f"{stem}.ffmpeg.log"

    srt_rows = [(s / 1000, e / 1000, top, bottom) for s, e, top, bottom in rows]
    write_srt(srt_rows, srt_path)
    write_ass(srt_rows, ass_path, margin_v=cfg["margin_v"], top_only=False,
              font="Microsoft YaHei")

    start_s = clip["start_ms"] / 1000
    length_s = clip["duration_ms"] / 1000
    if dub is not None:
        # Chinese intro narration over the original English audio: sidechain
        # ducking is applied in the same QSV pass that burns the subtitles.
        import dub_mix
        dub_cfg = {k: cfg[k] for k in ("duck_threshold", "duck_target_db", "duck_ratio",
                                       "dub_target_db", "attack_ms", "release_ms",
                                       "dub_gain", "sample_rate")
                   if k in cfg}
        dub_cfg["dub_gain"] = dub_mix.resolve_gain(dub, dub_cfg)
        dub_cfg["duck_threshold"] = dub_mix.resolve_threshold(dub, dub_cfg)
        cmd = [
            "ffmpeg", "-hide_banner", "-y",
            "-ss", f"{start_s:.3f}", "-i", str(video), "-i", str(dub),
            "-t", f"{length_s:.3f}",
            "-map_chapters", "-1",
            "-filter_complex", dub_mix.build_filter_complex(ass_path, dub_cfg),
            "-map", "[v]", "-map", "[aout]",
            "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]), "-preset", "slow",
            "-c:a", cfg["audio_codec"], "-b:a", cfg["audio_bitrate"],
            "-ar", str(int(dub_cfg.get("sample_rate", dub_mix.DEFAULTS["sample_rate"]))),
            "-sn", "-dn", "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero",
        ]
    else:
        cmd = [
            "ffmpeg", "-hide_banner", "-y",
            "-ss", f"{start_s:.3f}", "-i", str(video), "-t", f"{length_s:.3f}",
            "-map", "0:v:0", "-map", "0:a:0",
            "-map_chapters", "-1",
            "-vf", f"ass={escape_filter_path(ass_path)}",
            "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]), "-preset", "slow",
            "-c:a", cfg["audio_codec"], "-b:a", cfg["audio_bitrate"],
            "-sn", "-dn", "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero",
        ]
    if cfg["cfr"] == "on" or (cfg["cfr"] == "auto" and source_info["vfr"]):
        cmd += ["-fps_mode", "cfr", "-r", source_info["fps"]]
    cmd.append(str(tmp_path))

    proc = run_cmd(cmd, timeout=3600, log_path=ffmpeg_log)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg exit {proc.returncode}: {proc.stderr.strip()[-800:]}")
    return tmp_path, srt_path, [rel(ffmpeg_log)]


# --------------------------------------------------------------------------
# module 6: automatic acceptance
# --------------------------------------------------------------------------
def verify_clip(path: Path, clip: dict[str, Any], rows: list[tuple[int, int, str, str]],
                cfg: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    exists = path.exists() and path.stat().st_size > 0
    add("file_exists", exists, rel(path) if exists else "missing or empty")
    if not exists:
        return {"passed": False, "checks": checks}

    data: dict[str, Any] | None = None
    try:
        proc = run_cmd([
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(path),
        ], timeout=60)
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
    except Exception as exc:
        add("probe", False, str(exc))
    add("probe", data is not None, "ffprobe parsed" if data else "ffprobe failed")
    if data is None:
        return {"passed": False, "checks": checks}

    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    add("has_video", video_stream is not None,
        video_stream.get("codec_name", "") if video_stream else "no video stream")
    add("has_audio", audio_stream is not None,
        audio_stream.get("codec_name", "") if audio_stream else "no audio stream")
    add("video_codec", bool(video_stream) and video_stream.get("codec_name") == cfg["video_codec"],
        (video_stream or {}).get("codec_name", ""))
    add("audio_codec", bool(audio_stream) and audio_stream.get("codec_name") == cfg["audio_codec"],
        (audio_stream or {}).get("codec_name", ""))

    extras = [s for s in streams if s.get("codec_type") not in ("video", "audio")]
    add("only_av_streams", not extras,
        ", ".join(f"{s.get('index')}:{s.get('codec_type')}/{s.get('codec_name')}"
                  for s in extras) or "video + audio only")

    actual_ms = int(round(float(data["format"]["duration"]) * 1000))
    delta = actual_ms - clip["duration_ms"]
    add("duration", abs(delta) <= cfg["duration_tolerance_ms"],
        f"actual {actual_ms} ms vs target {clip['duration_ms']} ms (delta {delta:+d})")

    min_start = min((r[0] for r in rows), default=0)
    max_end = max((r[1] for r in rows), default=0)
    add("subtitle_bounds",
        min_start >= 0 and max_end <= clip["duration_ms"],
        f"subtitle span {min_start}–{max_end} ms, clip {clip['duration_ms']} ms")

    return {"passed": all(c["ok"] for c in checks), "checks": checks,
            "actual_duration_ms": actual_ms}


# --------------------------------------------------------------------------
# status machine
# --------------------------------------------------------------------------
def final_status(windows: list[dict[str, Any]], valid: list[dict[str, Any]],
                 clip_records: list[dict[str, Any]]) -> str:
    total = len(windows)
    failed_windows = sum(1 for w in windows if w["status"] != "OK")
    accepted = sum(1 for c in clip_records if c["acceptance"]["passed"])
    rejected = len(clip_records) - accepted

    if total == 0 or failed_windows == total:
        return "ANALYSIS_FAILED"
    if failed_windows:
        if not valid:
            return "ANALYSIS_FAILED"
        if rejected:
            return "FAILED"
        return "PARTIAL" if accepted else "FAILED"
    if not valid:
        return "NO_CANDIDATES"
    if rejected:
        return "FAILED"
    return "SUCCESS" if accepted else "FAILED"


# --------------------------------------------------------------------------
# main pipeline
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Auto highlight clipping (bilingual SRT + video)")
    ap.add_argument("--srt", default=None,
                    help="bilingual SRT (default: subtitles/<video-id>.zh.bilingual.srt)")
    ap.add_argument("--video", default=None)
    ap.add_argument("--video-id", default=None)
    ap.add_argument("--out", default=None, help="output dir (default clips/<video_id>)")
    ap.add_argument("--output-dir", dest="out", default=None,
                    help="alias for --out (isolated analysis runs)")
    ap.add_argument("--base", default=DEFAULTS["base_url"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-clips", type=int, default=DEFAULTS["max_clips"])
    ap.add_argument("--window-ms", type=int, default=DEFAULTS["window_ms"])
    ap.add_argument("--overlap-ms", type=int, default=DEFAULTS["overlap_ms"])
    ap.add_argument("--min-clip-ms", type=int, default=DEFAULTS["min_clip_ms"])
    ap.add_argument("--max-clip-ms", type=int, default=DEFAULTS["max_clip_ms"])
    ap.add_argument("--prefer-min-ms", type=int, default=DEFAULTS["prefer_min_ms"])
    ap.add_argument("--prefer-max-ms", type=int, default=DEFAULTS["prefer_max_ms"])
    ap.add_argument("--duration-tolerance-ms", type=int, default=DEFAULTS["duration_tolerance_ms"])
    ap.add_argument("--margin-v", type=int, default=DEFAULTS["margin_v"])
    ap.add_argument("--qsv-quality", type=int, default=DEFAULTS["qsv_quality"])
    ap.add_argument("--audio-bitrate", default=DEFAULTS["audio_bitrate"])
    ap.add_argument("--cfr", choices=("auto", "on", "off"), default="auto")
    ap.add_argument("--dub-dir", default=None,
                    help="directory holding per-clip narration tracks (clip-01.wav, ...); "
                         "when present, the dub is mixed with sidechain ducking in the same pass")
    ap.add_argument("--duck-threshold", type=float, default=None)
    ap.add_argument("--duck-target-db", type=float, default=None)
    ap.add_argument("--duck-ratio", type=float, default=None)
    ap.add_argument("--duck-attack-ms", type=int, default=None)
    ap.add_argument("--duck-release-ms", type=int, default=None)
    ap.add_argument("--dub-gain", type=float, default=None)
    ap.add_argument("--model-retries", type=int, default=DEFAULTS["model_retries"])
    ap.add_argument("--model-timeout", type=int, default=DEFAULTS["model_timeout_s"])
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--reuse-analysis", action="store_true",
                    help="render the existing analysis.json without calling the model again")
    ap.add_argument("--override-start", action="append", default=[], metavar="INDEX=TIME",
                    help="manually override a selected clip's start (1-based index), "
                         "e.g. 1=00:04:49.375; snapped to the containing cue's start")
    ap.add_argument("--fix-start", default=None, metavar="TIME",
                    help="shorthand for --override-start 1=TIME (e.g. 04:49.375)")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    problems: list[str] = []
    if args.overlap_ms >= args.window_ms:
        problems.append("overlap-ms must be smaller than window-ms")
    if args.min_clip_ms <= 0 or args.max_clip_ms < args.min_clip_ms:
        problems.append("require 0 < min-clip-ms <= max-clip-ms")
    if not (args.min_clip_ms <= args.prefer_min_ms <= args.prefer_max_ms <= args.max_clip_ms):
        problems.append("require min-clip-ms <= prefer-min-ms <= prefer-max-ms <= max-clip-ms")
    if args.max_clips < 1:
        problems.append("max-clips must be >= 1")
    if args.duration_tolerance_ms < 0:
        problems.append("duration-tolerance-ms must be >= 0")
    if problems:
        for problem in problems:
            print(f"config error: {problem}", file=sys.stderr)
        return 2

    try:
        overrides = parse_overrides(args.override_start)
        if args.fix_start:
            overrides.setdefault(1, parse_time_ms(args.fix_start))
    except ValueError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    video_id = args.video_id or (Path(args.srt).name.split(".")[0] if args.srt else "")
    if not args.srt and not video_id:
        print("config error: pass --srt or --video-id", file=sys.stderr)
        return 2
    srt_path = Path(args.srt) if args.srt else (
        ROOT / "subtitles" / f"{video_id}.zh.bilingual.srt")
    if not srt_path.is_absolute():
        srt_path = (ROOT / srt_path).resolve()
    if not srt_path.exists():
        print(f"config error: SRT not found: {srt_path}", file=sys.stderr)
        return 2
    out_dir = Path(args.out) if args.out else ROOT / "clips" / video_id
    if not out_dir.is_absolute():
        out_dir = (ROOT / out_dir).resolve()
    work_dir = out_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    RUN.log_path = out_dir / "run.log"
    RUN.log(f"=== auto_clip {now_iso()} ===")
    RUN.log(f"srt: {rel(srt_path)}")

    cfg: dict[str, Any] = {
        **{k: DEFAULTS[k] for k in DEFAULTS},
        "window_ms": args.window_ms,
        "overlap_ms": args.overlap_ms,
        "min_clip_ms": args.min_clip_ms,
        "max_clip_ms": args.max_clip_ms,
        "prefer_min_ms": args.prefer_min_ms,
        "prefer_max_ms": args.prefer_max_ms,
        "dup_overlap_ratio": DEFAULTS["dup_overlap_ratio"],
        "max_clips": args.max_clips,
        "duration_tolerance_ms": args.duration_tolerance_ms,
        "margin_v": args.margin_v,
        "qsv_quality": args.qsv_quality,
        "audio_bitrate": args.audio_bitrate,
        "base_url": args.base,
        "model": args.model,
        "model_retries": args.model_retries,
        "model_timeout_s": args.model_timeout,
        "cfr": args.cfr,
        "duck_threshold": (args.duck_threshold if args.duck_threshold is not None
                           else dub_mix.DEFAULTS["duck_threshold"]),
        "duck_target_db": (args.duck_target_db if args.duck_target_db is not None
                           else dub_mix.DEFAULTS["duck_target_db"]),
        "dub_target_db": dub_mix.DEFAULTS["dub_target_db"],
        "duck_ratio": (args.duck_ratio if args.duck_ratio is not None
                       else dub_mix.DEFAULTS["duck_ratio"]),
        "attack_ms": (args.duck_attack_ms if args.duck_attack_ms is not None
                      else dub_mix.DEFAULTS["attack_ms"]),
        "release_ms": (args.duck_release_ms if args.duck_release_ms is not None
                       else dub_mix.DEFAULTS["release_ms"]),
        "dub_gain": (args.dub_gain if args.dub_gain is not None
                     else dub_mix.DEFAULTS["dub_gain"]),
        "sample_rate": dub_mix.DEFAULTS["sample_rate"],
        "srt_path": srt_path,
        "video_path": Path(args.video).resolve() if args.video else None,
        "out_dir": out_dir,
    }

    cues, parse_errors = parse_bilingual_srt(srt_path)
    if parse_errors:
        RUN.log(f"SRT validation failed: {parse_errors[:3]}")
        result = {
            "schema_version": SCHEMA_VERSION, "video_id": video_id, "srt": rel(srt_path),
            "generated_at": now_iso(), "status": "FAILED", "analysis_complete": False,
            "config": {k: v for k, v in cfg.items()
                       if k not in ("srt_path", "video_path", "out_dir")},
            "errors": parse_errors, "windows": [], "candidates_raw": [],
            "candidates_valid": [], "candidates_removed": [], "clips": [],
        }
        write_json(out_dir / "result.json", result)
        return 1

    RUN.log(f"cues: {len(cues)} | span {fmt_hmsms(cues[0].start)} – {fmt_hmsms(cues[-1].end)}")
    analysis_path = out_dir / "analysis.json"
    if args.reuse_analysis:
        if not analysis_path.exists():
            RUN.log("--reuse-analysis given but analysis.json is missing")
            return 1
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        if analysis.get("video_id") != video_id or analysis.get("cue_count") != len(cues):
            RUN.log("analysis.json does not match this SRT; rerun without --reuse-analysis")
            return 1
        analysis.setdefault("config", {})["model"] = analysis.get("model")
        RUN.log(f"reusing {rel(analysis_path)} "
                f"({len(analysis['candidates_selected'])} selected candidates)")
    else:
        analysis = analyze(cues, cfg, video_id, work_dir)

    if args.analyze_only:
        analysis["source"] = (rel(cfg["video_path"])
                              if cfg["video_path"] and cfg["video_path"].exists() else None)
        write_json(out_dir / "analysis.json", analysis)
        RUN.log(f"analysis status: {analysis['analysis_status']}")
        return 0 if analysis["analysis_status"] != "ANALYSIS_FAILED" else 1

    if not cfg["video_path"] or not cfg["video_path"].exists():
        RUN.log("source video missing; cannot render")
        result = {**analysis, "status": "FAILED",
                  "errors": analysis["errors"] + ["source video missing"]}
        write_json(out_dir / "result.json", result)
        return 1

    try:
        source_info = probe_source(cfg["video_path"])
        RUN.log(f"source: {source_info['video_codec']} {source_info['fps']} "
                f"({source_info['duration_ms']} ms){' VFR' if source_info['vfr'] else ''}")
    except Exception as exc:
        RUN.log(f"source probe failed: {exc}")
        result = {**analysis, "status": "FAILED", "errors": analysis["errors"] + [str(exc)]}
        write_json(out_dir / "result.json", result)
        return 1

    analysis["source_duration_ms"] = source_info["duration_ms"]
    analysis["source"] = rel(cfg["video_path"])

    selected = analysis["candidates_selected"]
    override_plan: dict[int, dict[str, Any]] = {}
    for index, requested in sorted(overrides.items()):
        if index > len(selected):
            RUN.log(f"override index {index} out of range (selected clips: {len(selected)})")
            return 2
        cand = selected[index - 1]
        cue_id, applied = snap_to_cue_start(cues, requested)
        duration = cand["end_ms"] - applied
        if duration < cfg["min_clip_ms"] or duration > cfg["max_clip_ms"]:
            RUN.log(f"override for clip {index:02d} gives {duration} ms, outside "
                    f"[{cfg['min_clip_ms']}, {cfg['max_clip_ms']}]")
            return 2
        override_plan[index] = {
            "requested_ms": requested,
            "applied_ms": applied,
            "cue_id": cue_id,
            "original_start_ms": cand["start_ms"],
            "delta_ms": applied - cand["start_ms"],
            "duration_ms": duration,
        }
        RUN.log(f"override clip {index:02d}: {fmt_hmsms(cand['start_ms'])} → "
                f"{fmt_hmsms(applied)} (cue {cue_id}), duration {duration} ms")

    write_json(out_dir / "analysis.json", analysis)

    final_dir = out_dir / "final"
    quarantine_dir = out_dir / "quarantine"
    final_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    clip_records: list[dict[str, Any]] = []
    for index, cand in enumerate(analysis["candidates_selected"], 1):
        trim_ms = int(cand.get("trim_start_ms") or 0)
        start_ms, duration_ms = cand["start_ms"] + trim_ms, cand["duration_ms"]
        override = override_plan.get(index)
        if override is not None:
            start_ms, duration_ms = override["applied_ms"], override["duration_ms"]
            trim_ms = 0
        rows = clamp_cues(cues, start_ms, duration_ms)
        prefix = cand.get("trim_prefix") if trim_ms else None
        if prefix and rows:
            first = rows[0]
            rows[0] = (first[0], first[1],
                       _strip_prefix_from_text(first[2], prefix),
                       _strip_zh_filler(first[3]))
        clip = {
            "index": index,
            "source_window": cand["source_window"],
            "start_ms": start_ms,
            "end_ms": cand["end_ms"],
            "duration_ms": duration_ms,
            "trim_start_ms": trim_ms,
            "trim_prefix": cand.get("trim_prefix") if trim_ms else None,
            "title": cand["title"],
            "summary": cand["summary"],
            "subtitle_cues": len(rows),
            "subtitle_max_end_ms": max((r[1] for r in rows), default=0),
        }
        if override is not None:
            clip["start_override"] = {k: v for k, v in override.items() if k != "duration_ms"}
        RUN.log(f"clip {index:02d}: {fmt_hmsms(start_ms)}–{fmt_hmsms(cand['end_ms'])} "
                f"({duration_ms} ms, {len(rows)} cues) {cand['title']}")
        slug = slugify(cand["title"])
        name = f"{video_id}.highlight-{index:02d}" + (f".{slug}" if slug else "") + ".mp4"
        dub_path: Path | None = None
        if args.dub_dir:
            candidate = Path(args.dub_dir).resolve() / f"clip-{index:02d}.wav"
            if candidate.exists():
                dub_path = candidate
                clip["dub"] = rel(dub_path)
            else:
                RUN.log(f"clip {index:02d}: no dub track at {candidate}, rendering without narration")
        try:
            tmp_path, srt_path_clip, ffmpeg_logs = render_clip(
                cfg["video_path"], clip, rows, cfg, work_dir, index, source_info, dub_path)
            acceptance = verify_clip(tmp_path, clip, rows, cfg)
            clip.update(srt=rel(srt_path_clip),
                        ass=rel(work_dir / f"clip-{index:02d}.ass"),
                        work_logs=ffmpeg_logs, acceptance=acceptance)
            if acceptance["passed"]:
                target = final_dir / name
                os.replace(tmp_path, target)
                clip["path"] = rel(target)
                RUN.log(f"clip {index:02d} accepted → {rel(target)}")
            else:
                target = quarantine_dir / name
                os.replace(tmp_path, target)
                clip["path"] = rel(target)
                clip["quarantined"] = True
                failed_checks = [c["name"] for c in acceptance["checks"] if not c["ok"]]
                (quarantine_dir / f"{name}.failed.json").write_text(
                    json.dumps(clip, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                RUN.log(f"clip {index:02d} REJECTED ({failed_checks}) → {rel(target)}")
        except Exception as exc:
            clip["acceptance"] = {"passed": False, "checks": [
                {"name": "render", "ok": False, "detail": str(exc)}]}
            clip["path"] = None
            RUN.log(f"clip {index:02d} render failed: {exc}")
        clip_records.append(clip)

    status = final_status(analysis["windows"], analysis["candidates_valid"], clip_records)
    result = {
        **analysis,
        "status": status,
        "clips": clip_records,
        "manual_overrides": [
            {"clip_index": c["index"], **c["start_override"]}
            for c in clip_records if "start_override" in c
        ],
        "final_dir": rel(final_dir),
        "quarantine_dir": rel(quarantine_dir),
    }
    write_json(out_dir / "result.json", result)
    RUN.log(f"final status: {status} "
            f"(windows {len(analysis['windows'])}, "
            f"valid {len(analysis['candidates_valid'])}, "
            f"accepted {sum(1 for c in clip_records if c['acceptance']['passed'])})")
    return 0 if status in ("SUCCESS", "PARTIAL", "NO_CANDIDATES") else 1


if __name__ == "__main__":
    sys.exit(main())
