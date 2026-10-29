"""Ask the local Qwen model for a short Chinese dub script (JSON, no timings).

The LLM writes words only; every time value is computed here so the result is
deterministic and safe to hand to synthesize_dub.py.

Usage:
    uv run python scripts/make_dub_script.py --result clips/<id>/result.json --clip 1
    uv run python scripts/make_dub_script.py --text "..." --title "..." --out dub/x.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_clip as ac  # noqa: E402

DEFAULTS: dict[str, Any] = {
    "base_url": "http://127.0.0.1:8080",
    "sentences": 3,
    "max_chars": 30,
    "min_chars": 12,
    "gap_s": 0.35,
    "tail_s": 0.25,
    "chars_per_sec": 4.3,
    "min_budget_s": 2.5,
    "max_budget_s": 6.0,
    "temperature": 0.35,
    "timeout_s": 300,
}

SYSTEM = (
    "你是中文科技视频的资深旁白撰稿人。只输出一个严格合法的 JSON 数组，"
    "不输出解释、不输出 Markdown、不输出任何时间字段。"
)


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


def extract_json_array(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        raise ValueError(f"no JSON array in model output: {text[:200]}")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("model output is not an array")
    return data


def clip_context(result_path: Path, clip_index: int) -> tuple[dict[str, Any], str]:
    data = json.loads(result_path.read_text(encoding="utf-8"))
    clip = next((c for c in data.get("clips", []) if c.get("index") == clip_index), None)
    if clip is None:
        raise SystemExit(f"clip {clip_index} not in {result_path}")
    if not clip.get("srt"):
        raise SystemExit(f"clip {clip_index} has no SRT (was it rendered?)")
    srt_path = resolve(clip["srt"])
    cues, errors = ac.parse_bilingual_srt(srt_path)
    if errors:
        raise SystemExit(f"SRT parse errors: {errors[:3]}")
    # clip["srt"] is already clamped and rebased to 0; take the opening cues.
    lines = [cue.bottom or cue.top for cue in cues[:14]]
    return clip, "\n".join(lines)


def build_prompt(title: str, summary: str, excerpt: str, count: int) -> str:
    return (
        f"高光片段标题：{title}\n"
        f"片段摘要：{summary}\n"
        f"片头原声（中文字幕，前 1 分钟）：\n{excerpt}\n\n"
        f"请为这个片段写 {count} 句中文导读，用于片头配音，要求：\n"
        f"1. 第一句是钩子，直接抛出一个反直觉的判断或数字；\n"
        f"2. 后续句子交代讲话者与核心论点，最后一句自然把听众交还给原声；\n"
        f"3. 每句 {DEFAULTS['min_chars']}–{DEFAULTS['max_chars']} 个汉字，口语、沉稳、有信息量；\n"
        f"4. 不要出现英文完整句子，专有名词可保留原文；\n"
        f"5. 只输出 JSON 数组：[{{\"text\": \"...\"}}]。"
    )


def call_model(base: str, prompt: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    model = ac.discover_model(base)
    resp = requests.post(
        f"{base}/v1/chat/completions",
        json={"model": model,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": prompt}],
              "temperature": cfg["temperature"]},
        timeout=(10, cfg["timeout_s"]),
    )
    if resp.status_code != 200:
        raise SystemExit(f"model HTTP {resp.status_code}: {resp.text[:300]}")
    content = resp.json()["choices"][0]["message"]["content"]
    data = extract_json_array(content)
    if isinstance(data, list) and data and isinstance(data[0], str):
        data = [{"text": item} for item in data]
    return data


def validate(items: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    texts = [str(item.get("text", "")).strip() for item in items]
    problems = []
    if not 2 <= len(texts) <= 5:
        problems.append(f"need 2-5 sentences, got {len(texts)}")
    for index, text in enumerate(texts, 1):
        if not cfg["min_chars"] <= len(text) <= cfg["max_chars"] + 6:
            problems.append(f"sentence {index} has {len(text)} chars: {text[:20]}")
        if re.search(r"[A-Za-z]{6,}", text) and not re.search(r"SemiAnalysis|NVIDIA|OpenAI|Google|Meta|CPU|GPU|AI", text):
            problems.append(f"sentence {index} looks English-heavy: {text[:20]}")
    return problems


def with_timing(texts: list[str], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    sentences = []
    cursor = 0.0
    for index, text in enumerate(texts, 1):
        budget = round(min(cfg["max_budget_s"],
                           max(cfg["min_budget_s"], len(text) / cfg["chars_per_sec"] + 0.7)), 2)
        sentences.append({
            "sentence_id": index,
            "target_start_sec": round(cursor, 2),
            "max_duration_sec": budget,
            "text": text,
        })
        cursor += budget + cfg["gap_s"]
    return sentences


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a structured Chinese dub script with local Qwen")
    ap.add_argument("--result", default=None, help="clips/<id>/result.json")
    ap.add_argument("--clip", type=int, default=1, help="1-based clip index (with --result)")
    ap.add_argument("--title", default="", help="override title")
    ap.add_argument("--summary", default="", help="override summary / text context")
    ap.add_argument("--text", default=None, help="raw context text instead of a result clip")
    ap.add_argument("--sentences", type=int, default=DEFAULTS["sentences"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--base", default=DEFAULTS["base_url"])
    ap.add_argument("--retries", type=int, default=1)
    args = ap.parse_args()

    cfg = {**DEFAULTS, "sentences": args.sentences}
    if args.text:
        title, summary, excerpt = args.title or "（未命名片段）", args.summary, args.text
    else:
        if not args.result:
            print("need --result or --text", file=sys.stderr)
            return 2
        clip, excerpt = clip_context(resolve(args.result), args.clip)
        title, summary = args.title or clip.get("title", ""), args.summary or clip.get("summary", "")

    prompt = build_prompt(title, summary, excerpt, cfg["sentences"])
    problems: list[str] = []
    for attempt in range(args.retries + 1):
        items = call_model(args.base, prompt, cfg)
        problems = validate(items, cfg)
        if not problems:
            break
        log(f"attempt {attempt + 1} rejected: {problems[:3]}")
    if problems:
        log("model output still invalid; inspect the raw sentences above and edit manually")
        return 1

    texts = [str(item["text"]).strip() for item in items]
    sentences = with_timing(texts, cfg)
    if args.out:
        out_path = resolve(args.out)
    else:
        stem = f"clip-{args.clip:02d}" if args.result else "dub"
        out_path = ROOT / "dub" / Path(args.result).resolve().parent.name / f"{stem}.script.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sentences, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total = sentences[-1]["target_start_sec"] + sentences[-1]["max_duration_sec"]
    log(f"wrote {rel(out_path)}: {len(sentences)} sentences, narration window {total:.1f}s")
    for s in sentences:
        log(f"  #{s['sentence_id']} start={s['target_start_sec']:5.2f}s "
            f"budget={s['max_duration_sec']:4.2f}s | {s['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
