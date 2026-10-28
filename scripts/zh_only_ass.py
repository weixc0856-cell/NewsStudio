"""Write a Chinese-only ASS from a bilingual (EN top / ZH bottom) SRT.

Use when the source video already has English subtitles burned into the picture:
per the project rules we do not add a second English line, only Chinese above
the hardcoded ones.

Usage:
    uv run python scripts/zh_only_ass.py subtitles/<id>.zh.bilingual.srt \
        --out subtitles/<id>.zh.ass --margin-v 280
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_subs import write_ass  # noqa: E402

CUE_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2})[,.](\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2})[,.](\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
    re.S,
)


def _ts(hms: str, ms: str) -> float:
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--out", default="")
    ap.add_argument("--margin-v", type=int, default=280)
    ap.add_argument("--font", default="Microsoft YaHei")
    args = ap.parse_args()

    raw = Path(args.srt).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    rows = []
    for m in CUE_RE.finditer(raw):
        start = _ts(m.group(1), m.group(2))
        end = _ts(m.group(3), m.group(4))
        lines = [ln.strip() for ln in m.group(5).strip().splitlines() if ln.strip()]
        zh = lines[-1] if lines else ""
        if zh:
            rows.append((start, end, "", zh))

    out = Path(args.out) if args.out else Path(args.srt).with_suffix(".ass")
    # top_only=False so _wrap_cjk runs on the bottom slot; the top is empty.
    write_ass(rows, out, margin_v=args.margin_v, top_only=False, font=args.font)
    fixed = []
    for line in out.read_text(encoding="utf-8").splitlines():
        marker = ",," + chr(92) + "N"
        if line.startswith("Dialogue:") and marker in line:
            line = line.replace(marker, ",,", 1)
        fixed.append(line)
    out.write_text("\n".join(fixed) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(rows)} cues, zh only, MarginV={args.margin_v})")


if __name__ == "__main__":
    main()
