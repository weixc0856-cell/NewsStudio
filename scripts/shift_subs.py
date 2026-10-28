"""Shift subtitle timings (ASS or SRT) by a number of seconds.

Used when trimming the video: subtitles must move with the cut.
Usage: uv run python scripts/shift_subs.py in.ass out.ass -3
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ASS_DLG = re.compile(
    r"^(Dialogue: [^,]*,)"
    r"(\d+):(\d{2}):(\d{2})\.(\d{2}),"
    r"(\d+):(\d{2}):(\d{2})\.(\d{2}),(.*)$"
)
SRT_TS = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})$"
)


def fmt_ass(t: float) -> str:
    cs = int(round(max(t, 0) * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def fmt_srt(t: float) -> str:
    ms = int(round(max(t, 0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def shift_ass(text: str, delta: float) -> str:
    out = []
    for line in text.splitlines():
        m = ASS_DLG.match(line)
        if not m:
            out.append(line)
            continue
        start = int(m[2]) * 3600 + int(m[3]) * 60 + int(m[4]) + int(m[5]) / 100
        end = int(m[6]) * 3600 + int(m[7]) * 60 + int(m[8]) + int(m[9]) / 100
        if end + delta <= 0:
            continue
        start = max(0.0, start + delta)
        end = max(start + 0.2, end + delta)
        out.append(f"{m[1]}{fmt_ass(start)},{fmt_ass(end)},{m[10]}")
    return "\n".join(out) + "\n"


def shift_srt(text: str, delta: float) -> str:
    blocks = re.split(r"\n\s*\n", text.strip())
    out = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 2:
            continue
        m = SRT_TS.match(lines[1].strip())
        if not m:
            continue
        start = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
        end = int(m[5]) * 3600 + int(m[6]) * 60 + int(m[7]) + int(m[8]) / 1000
        if end + delta <= 0:
            continue
        start = max(0.0, start + delta)
        end = max(start + 0.2, end + delta)
        out.append("\n".join([str(len(out) + 1), f"{fmt_srt(start)} --> {fmt_srt(end)}", *lines[2:]]))
    return "\n\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("offset", type=float)
    ap.add_argument("--encoding", default="utf-8")
    args = ap.parse_args()

    src = Path(args.src)
    text = src.read_text(encoding=args.encoding, errors="replace")
    if src.suffix.lower() == ".ass":
        result = shift_ass(text, args.offset)
    elif src.suffix.lower() == ".srt":
        result = shift_srt(text, args.offset)
    else:
        sys.exit("expected .ass or .srt")
    Path(args.dst).write_text(result, encoding=args.encoding, newline="\n")
    print(f"wrote {args.dst} (offset {args.offset:+.2f}s)")


if __name__ == "__main__":
    main()
