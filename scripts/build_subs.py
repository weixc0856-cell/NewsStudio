"""Build subtitle files from yt-dlp auto-caption downloads.

YouTube's json3 auto captions are word-chunk events whose durations overlap and
whose text is incremental ("Chancellor, if you" / "could switch" / "jobs,").
This module turns them into sentence-level cues, then writes:
  subtitles/bilingual.srt  - original language on top, Chinese below
  subtitles/en.ass         - single language, positioned above burned-in subtitles
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB_DIR = ROOT / "subtitles"

ABBREV = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "jr.", "sr.", "vs.", "etc.",
    "inc.", "ltd.", "corp.", "co.", "u.s.", "u.k.", "e.g.", "i.e.", "no.",
}
SENT_END = re.compile(r"[.!?][\"'’”)\]]*$")


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">"))
    text = re.sub(r"(?:^|\s)>>\s*", " ", text)
    text = re.sub(r"(?:^|\n)\s*SPEAKER\s+\d+:\s*", " ", text, flags=re.I)
    text = re.sub(r"(?:^|\n)\s*(?:ANNOUNCER|MODERATOR|HOST|NARRATOR):\s*", " ", text, flags=re.I)
    text = re.sub(r"(?:^|\n)\s*(?:[A-Z][A-Z.'-]*\s+)+[A-Z][A-Z.'-]*:\s*", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"^-\s+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_json3(path: Path) -> list[tuple[float, float, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    events = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = clean("".join(s.get("utf8", "") for s in segs))
        if text:
            events.append((ev.get("tStartMs", 0) / 1000, ev.get("dDurationMs", 0) / 1000, text))
    return events


CUE_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
    re.S,
)


def _ts(value: str) -> float:
    h, m, rest = value.split(":")
    s, ms = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(path: Path) -> list[tuple[float, float, str]]:
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    events = []
    for m in CUE_RE.finditer(raw):
        text = clean(" ".join(m.group(3).splitlines()))
        if text and text != "WEBVTT":
            events.append((_ts(m.group(1)), _ts(m.group(2)) - _ts(m.group(1)), text))
    return events


def events_to_words(events: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    """Spread each chunk's words over [chunk_start, next_chunk_start) for monotonic timing."""
    events = sorted(events)
    words: list[tuple[float, float, str]] = []
    for i, (start, dur, text) in enumerate(events):
        end = events[i + 1][0] if i + 1 < len(events) else start + max(dur, 0.4)
        if end <= start:
            end = start + 0.3
        tokens = text.split()
        if not tokens:
            continue
        weights = [len(t) + 1 for t in tokens]
        total = sum(weights)
        cursor = start
        for token, weight in zip(tokens, weights):
            step = (end - start) * weight / total
            words.append((cursor, cursor + step, token))
            cursor += step
    return words


def _split_long(tokens: list[tuple[float, float, str]]) -> list[list[tuple[float, float, str]]]:
    """Split an over-long sentence at punctuation near its midpoint."""
    text = " ".join(t for _, _, t in tokens)
    duration = tokens[-1][1] - tokens[0][0]
    if len(text) <= 150 and duration <= 12:
        return [tokens]
    candidates = [
        i for i, (_, _, tok) in enumerate(tokens[:-1])
        if tok.rstrip("\"')]").endswith((",", ";", ":", "-", "—"))
    ]
    midpoint = len(text) / 2
    if candidates:
        idx = min(candidates, key=lambda i: abs(len(" ".join(t for _, _, t in tokens[:i + 1])) - midpoint))
        left, right = tokens[:idx + 1], tokens[idx + 1:]
        if left and right:
            return _split_long(left) + _split_long(right)
    mid = len(tokens) // 2
    if 0 < mid < len(tokens):
        return _split_long(tokens[:mid]) + _split_long(tokens[mid:])
    return [tokens]


def words_to_sentences(words: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    sentences: list[list[tuple[float, float, str]]] = []
    current: list[tuple[float, float, str]] = []
    for start, end, token in words:
        current.append((start, end, token))
        bare = token.lower().strip("\"'()[]")
        if SENT_END.search(token) and bare not in ABBREV:
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)

    # 1) Merge fragments into the preceding sentence.
    merged_sents: list[list[tuple[float, float, str]]] = []
    for sent in sentences:
        text = " ".join(t for _, _, t in sent)
        if merged_sents:
            prev_text = " ".join(t for _, _, t in merged_sents[-1])
            continues = not SENT_END.search(prev_text.rstrip("\"'”’")) and len(text) < 30
            if continues or (text[:1].islower() and len(text) < 40):
                merged_sents[-1] = merged_sents[-1] + sent
                continue
        merged_sents.append(sent)

    # 2) Split sentences that are too long for one cue.
    pieces: list[list[tuple[float, float, str]]] = []
    for sent in merged_sents:
        pieces.extend(_split_long(sent))

    cues: list[tuple[float, float, str]] = []
    for i, sent in enumerate(pieces):
        text = " ".join(t for _, _, t in sent)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        start = sent[0][0]
        end = sent[-1][1]
        if i + 1 < len(pieces):
            nxt = pieces[i + 1][0][0]
            end = min(end + 0.2, nxt - 0.05) if nxt - end > 0.35 else nxt - 0.05
        cues.append((start, max(end, start + 0.4), text))

    for i in range(len(cues) - 1):
        start, end, text = cues[i]
        next_start = cues[i + 1][0]
        if end > next_start - 0.03:
            cues[i] = (start, max(start + 0.3, next_start - 0.03), text)
    return cues


SRT_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
    re.S,
)


def _srt_ts(value: str) -> float:
    h, m, rest = value.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    cues = []
    for m in SRT_RE.finditer(raw):
        text = clean(" ".join(m.group(3).splitlines()))
        if text:
            cues.append((_srt_ts(m.group(1)), _srt_ts(m.group(2)), text))
    return cues


def merge_manual_cues(events: list[tuple[float, float, str]],
                      max_chars: int = 130, max_dur: float = 8.0) -> list[tuple[float, float, str]]:
    """Manual captions are timed fragments; join them into sentences for translation context."""
    events = sorted(events)
    out: list[tuple[float, float, str]] = []
    buf: list[tuple[float, float, str]] = []
    for start, end, text in events:
        if buf and start - buf[-1][1] > 1.5:
            out.append((buf[0][0], max(buf[-1][1], buf[0][0] + 0.3),
                        " ".join(item[2] for item in buf)))
            buf = []
        buf.append((start, end, text))
        joined = " ".join(item[2] for item in buf)
        span = buf[-1][1] - buf[0][0]
        finished = (SENT_END.search(text.rstrip("\"'”’")) and len(joined) >= 8)
        if finished or len(joined) >= max_chars or span >= max_dur:
            cut = len(buf)
            if not finished and len(buf) > 1:
                punct = [i for i, (_, _, t) in enumerate(buf[:-1])
                         if t.rstrip("\"'”’").endswith((",", ";", ":", "-", "—"))]
                if punct:
                    cut = punct[-1] + 1
            left, right = buf[:cut], buf[cut:]
            out.append((left[0][0], max(left[-1][1], left[0][0] + 0.3),
                        " ".join(item[2] for item in left)))
            buf = right
    if buf:
        out.append((buf[0][0], max(buf[-1][1], buf[0][0] + 0.3), " ".join(item[2] for item in buf)))
    return out


def load_cues(lang: str, video_id: str | None = None, manual: bool = False,
              raw: bool = False) -> list[tuple[float, float, str]]:
    for ext, parser in (("srt", parse_srt), ("json3", parse_json3), ("vtt", parse_vtt)):
        patterns = ([f"{video_id}.{lang}.{ext}", f"{video_id}.*.{lang}.{ext}"]
                    if video_id else [f"*.{lang}.{ext}"])
        hits = sorted({p for pattern in patterns for p in SUB_DIR.glob(pattern)})
        if hits:
            print(f"using {hits[0].name}")
            events = parser(hits[0])
            if manual and ext != "srt":
                events = [(s, s + max(d, 0.3), t) for s, d, t in events]
                if not raw:
                    events = merge_manual_cues(events)
                fixed = []
                for s, e, t in events:
                    if fixed:
                        ps, pe, pt = fixed[-1]
                        if (not SENT_END.search(pt.rstrip("\"'”’"))
                                and len(t) < 40 and s <= pe + 1.0):
                            fixed[-1] = (ps, max(pe, e), f"{pt} {t}".strip())
                            continue
                    fixed.append((s, e, t))
                return fixed
            if manual or ext == "srt":
                cues = sorted(events)
                fixed = []
                for i, (s, e, t) in enumerate(cues):
                    if i + 1 < len(cues) and e > cues[i + 1][0] - 0.03:
                        e = max(s + 0.2, cues[i + 1][0] - 0.03)
                    fixed.append((s, e, t))
                return fixed
            return words_to_sentences(events_to_words(events))
    return []


def overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def align(top: list, bottom: list) -> list[tuple[float, float, str, str]]:
    if not bottom:
        return [(s, e, t, "") for s, e, t in top]
    rows = []
    for start, end, text in top:
        picked: list[str] = []
        for b_start, b_end, b_text in bottom:
            if b_start > end:
                break
            if b_end < start:
                continue
            if overlap((start, end), (b_start, b_end)) > 0.1 and b_text not in picked:
                picked.append(b_text)
        if not picked:
            near = min(bottom, key=lambda b: abs(b[0] - start))
            if abs(near[0] - start) < 2.0:
                picked = [near[2]]
        rows.append((start, end, text, " ".join(picked)))
    return rows


def fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(rows, path: Path) -> None:
    blocks = []
    for i, (start, end, top, bottom) in enumerate(rows, 1):
        body = top if not bottom else f"{top}\n{bottom}"
        blocks.append(f"{i}\n{fmt_srt(start)} --> {fmt_srt(end)}\n{body}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")
    print(f"wrote {path} ({len(rows)} cues)")


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 2560
PlayResY: 1440
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},62,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3.2,1.4,2,160,160,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def fmt_ass(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def _latin_bounds(text: str, cut: int) -> tuple[int, int]:
    start = cut
    while start > 0 and text[start - 1].isascii() and (text[start - 1].isalnum() or text[start - 1] in " .-_/"):
        start -= 1
    end = cut
    while end < len(text) and text[end].isascii() and (text[end].isalnum() or text[end] in " .-_/"):
        end += 1
    return start, end


def _safe_cut(text: str, cut: int, target: int, limit: int) -> int:
    """Do not split a Latin word/acronym across a hard CJK line break."""
    if cut <= 0 or cut >= len(text):
        return cut
    if not (text[cut - 1].isascii() and text[cut - 1].isalnum()
            and text[cut].isascii() and text[cut].isalnum()):
        return cut
    start, end = _latin_bounds(text, cut)
    valid = [c for c in (start, end) if 0 < c <= limit and c < len(text)]
    if valid:
        return min(valid, key=lambda c: abs(c - target))
    return cut


def _wrap_cjk(text: str, limit: int = 50) -> list[str]:
    """libass does not break CJK lines at character boundaries, so add hard breaks."""
    if len(text) <= limit:
        return [text]
    lines: list[str] = []
    rest = text
    while len(rest) > limit:
        if len(rest) <= limit * 2:
            target = len(rest) // 2
            best = -1
            for p in "，。；：、,.!?;:":
                idx = rest.rfind(p, max(0, target - 10), min(len(rest), target + 10))
                if idx != -1 and (best == -1 or abs(idx + 1 - target) < abs(best + 1 - target)):
                    best = idx
            cut = best + 1 if best != -1 else target
            if cut <= 0 or cut >= len(rest):
                cut = target
            cut = _safe_cut(rest, cut, target, limit)
            lines.append(rest[:cut])
            rest = rest[cut:].lstrip()
            break
        window = rest[:limit]
        cut = max(window.rfind(p) for p in "，。；：、,.!?;:") + 1
        if cut < limit // 2:
            cut = limit
        cut = _safe_cut(rest, cut, limit, limit)
        lines.append(rest[:cut])
        rest = rest[cut:].lstrip()
    if rest:
        lines.append(rest)
    return lines


def write_ass(rows, path: Path, margin_v: int = 340, top_only: bool = True, font: str = "Arial") -> None:
    lines = [ASS_HEADER.format(margin_v=margin_v, font=font)]
    for start, end, top, bottom in rows:
        def esc(text: str) -> str:
            return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
        if top_only or not bottom:
            text = esc(top)
        else:
            text = esc(top) + "\\N" + "\\N".join(esc(part) for part in _wrap_cjk(bottom))
        lines.append(f"Dialogue: 0,{fmt_ass(start)},{fmt_ass(end)},Sub,,0,0,0,,{text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(rows)} cues, MarginV={margin_v})")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--top", default="en", help="original-language subtitle code")
    ap.add_argument("--bottom", default="zh-Hans", help="Chinese subtitle code")
    ap.add_argument("--prefix", default="", help="output filename prefix, e.g. '<video-id>.'")
    ap.add_argument("--id", default=None, help="video id whose subtitle files to load")
    ap.add_argument("--manual", action="store_true",
                    help="treat the source as manually-timed cues instead of auto word chunks")
    ap.add_argument("--raw", action="store_true",
                    help="with --manual, keep the original cue breaks instead of merging into sentences")
    ap.add_argument("--margin-v", type=int, default=350,
                    help="bottom margin in PlayRes units (350 clears burned-in Chinese, ~100 for clean video)")
    ap.add_argument("--start", type=float, default=0.0, help="keep cues after this source timestamp")
    ap.add_argument("--end", type=float, default=None, help="keep cues before this source timestamp")
    args = ap.parse_args()

    top = load_cues(args.top, args.id, manual=args.manual, raw=args.raw)
    bottom = load_cues(args.bottom, args.id, manual=args.manual, raw=args.raw)
    if not top:
        raise SystemExit(f"no {args.top} subtitles found")
    if args.start or args.end is not None:
        limit = args.end if args.end is not None else float("inf")
        top = [(max(0.0, s - args.start), min(e, limit) - args.start, t)
               for s, e, t in top if e > args.start and s < limit]
        bottom = [(max(0.0, s - args.start), min(e, limit) - args.start, t)
                  for s, e, t in bottom if e > args.start and s < limit]
    rows = align(top, bottom)
    write_srt(rows, SUB_DIR / f"{args.prefix}bilingual.srt")
    write_ass(rows, SUB_DIR / f"{args.prefix}{args.top}.ass", margin_v=args.margin_v)
    write_ass(rows, SUB_DIR / f"{args.prefix}bilingual.ass", margin_v=args.margin_v,
              top_only=False, font="Microsoft YaHei")


if __name__ == "__main__":
    main()
