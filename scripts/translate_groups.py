"""Translate sentence groups and split the Chinese back onto their cues.

Batch translation can shift lines when the model merges adjacent fragments.
This script groups consecutive cues until a sentence end, translates each
group as one unit, then splits the Chinese proportionally to the English
lengths so every cue keeps its own slice.

Usage:
    uv run python scripts/translate_groups.py subtitles/<id>.bilingual.srt \
        --out-prefix <id>.zh.group --margin-v 100
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SUB_DIR = ROOT / "subtitles"
sys.path.insert(0, str(ROOT / "scripts"))

from build_subs import write_ass, write_srt  # noqa: E402
from translate_local import SYSTEM, model_id  # noqa: E402

CUE_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2})[,.](\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2})[,.](\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
    re.S,
)
SENT_END = re.compile(r"[.!?][\"'’”)\]]*$")
SPLIT_P = set("，。；：、,.!?;:")


def _ts(hms: str, ms: str) -> float:
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def translate(base: str, model: str, text: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "把下面这段英文字幕译成简体中文，只输出一段中文译文，不要编号、不要解释：\n" + text},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
        "stream": False,
    }
    for attempt in range(4):
        try:
            r = requests.post(f"{base}/v1/chat/completions", json=payload, timeout=300)
            r.raise_for_status()
            out = r.json()["choices"][0]["message"]["content"].strip()
            out = re.sub(r"^\s*\d+\s*[.、)．]\s*", "", out)
            if out:
                return " ".join(out.splitlines()).strip()
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                print(f"  failed: {exc}", flush=True)
                return ""
            time.sleep(2)
    return ""


def split_cn(cn: str, weights: list[int]) -> list[str]:
    """Split a Chinese translation proportionally to the English cue lengths."""
    n = len(weights)
    if n == 1:
        return [cn]
    total = sum(weights)
    bounds = []
    acc = 0
    for w in weights[:-1]:
        acc += w
        bounds.append(round(len(cn) * acc / total))
    parts = []
    prev = 0
    for b in bounds:
        cut = b
        # prefer a punctuation break near the boundary
        best = None
        for p in range(max(prev + 1, b - 8), min(len(cn) - 1, b + 8)):
            if cn[p] in SPLIT_P:
                if best is None or abs(p + 1 - b) < abs(best + 1 - b):
                    best = p
        if best is not None:
            cut = best + 1
        if cut <= prev:
            cut = min(prev + 1, len(cn))
        parts.append(cn[prev:cut].strip())
        prev = cut
    parts.append(cn[prev:].strip())
    return parts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--out-prefix", default="")
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    ap.add_argument("--margin-v", type=int, default=100)
    ap.add_argument("--font", default="Microsoft YaHei")
    args = ap.parse_args()

    raw = Path(args.srt).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    cues = []
    for m in CUE_RE.finditer(raw):
        lines = [ln.strip() for ln in m.group(5).strip().splitlines() if ln.strip()]
        cues.append((_ts(m.group(1), m.group(2)), _ts(m.group(3), m.group(4)), lines[0]))

    # group until sentence end (max 3 cues)
    groups: list[list[int]] = []
    cur: list[int] = []
    for i, (_, _, en) in enumerate(cues):
        cur.append(i)
        if SENT_END.search(en) or len(cur) >= 3:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)

    model = model_id(args.base)
    print(f"model: {model} | cues: {len(cues)} | groups: {len(groups)}", flush=True)
    zh = [""] * len(cues)
    for gi, g in enumerate(groups, 1):
        text = " ".join(cues[i][2] for i in g)
        cn = translate(args.base, model, text)
        weights = [len(cues[i][2]) for i in g]
        for i, part in zip(g, split_cn(cn, weights)):
            zh[i] = part
        if gi % 20 == 0:
            print(f"  translated group {gi}/{len(groups)}", flush=True)

    missing = sum(1 for x in zh if not x.strip())
    if missing:
        print(f"WARNING: {missing} cues without translation", flush=True)
    rows = [(s, e, en, cn) for (s, e, en), cn in zip(cues, zh)]
    prefix = args.out_prefix or Path(args.srt).stem
    out_srt = SUB_DIR / f"{prefix}.bilingual.srt"
    out_ass = SUB_DIR / f"{prefix}.bilingual.ass"
    write_srt(rows, out_srt)
    write_ass(rows, out_ass, margin_v=args.margin_v, top_only=False, font=args.font)
    print(f"done: {out_srt} / {out_ass}", flush=True)


if __name__ == "__main__":
    main()
