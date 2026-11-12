"""Collect a YouTube transcript into the shared Docling source tree.

Raw material:  <docling-root>/input/youtube/<video-id>/
Processed:     <docling-root>/output/youtube/<video-id>/
Catalog:       <docling-root>/output/catalog.json

The collector prefers creator subtitles, then YouTube auto-captions, then a
local faster-whisper transcription.  It preserves the original text and source
timestamps; it does not summarize or rewrite the talk.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT))
import env_file  # noqa: E402,F401  # 载入仓库根 .env（本机路径/密钥不进 Git）

from build_subs import clean, parse_vtt  # noqa: E402

YTDLP = ROOT / ".venv" / "Scripts" / "yt-dlp.exe"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

SRT_CUE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
    re.S,
)


def run(cmd: list[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{detail[-2000:]}")
    return result


def ytdlp_json(url: str) -> dict:
    result = run(
        [
            str(YTDLP),
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--no-playlist",
            url,
        ]
    )
    return json.loads(result.stdout)


def pick_language(info: dict, requested: str) -> tuple[str, str | None]:
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    def match(keys: dict, wanted: str) -> str | None:
        if wanted in keys:
            return wanted
        base = wanted.split("-")[0].lower()
        for key in keys:
            if key.lower() == wanted.lower() or key.lower().split("-")[0] == base:
                return key
        return None

    if requested and requested != "auto":
        key = match(manual, requested)
        if key:
            return key, "manual"
        key = match(auto, requested)
        if key:
            return key, "auto"
        return requested, None

    for wanted in ("en", "en-US", "en-GB"):
        key = match(manual, wanted)
        if key:
            return key, "manual"
        key = match(auto, wanted)
        if key:
            return key, "auto"
    if manual:
        return next(iter(manual)), "manual"
    if auto:
        return next(iter(auto)), "auto"
    return "en", None


def download_subs(url: str, video_id: str, lang: str, source: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    flag = "--write-subs" if source == "manual" else "--write-auto-subs"
    run(
        [
            str(YTDLP),
            "--skip-download",
            flag,
            "--sub-langs",
            lang,
            "--sub-format",
            "vtt",
            "--paths",
            str(dest),
            "-o",
            "%(id)s.%(ext)s",
            "--no-warnings",
            "--no-playlist",
            url,
        ]
    )
    candidates = sorted(dest.glob(f"{video_id}*.vtt"))
    if not candidates:
        raise RuntimeError(f"yt-dlp reported {source} subtitles but wrote no VTT under {dest}")
    candidates.sort(key=lambda p: (lang not in p.name, len(p.name)))
    target = dest / "transcript.original.vtt"
    chosen = candidates[0]
    for extra in candidates[1:]:
        extra.unlink(missing_ok=True)
    if chosen != target:
        if target.exists():
            target.unlink()
        chosen.replace(target)
    return target


def download_audio(url: str, video_id: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(YTDLP),
            "-f",
            "ba/b",
            "--no-playlist",
            "--no-warnings",
            "--paths",
            str(dest),
            "-o",
            "%(id)s.%(ext)s",
            url,
        ]
    )
    candidates = [
        p for p in dest.glob(f"{video_id}.*")
        if p.suffix.lower() not in {".vtt", ".json", ".srt", ".md"}
    ]
    if not candidates:
        raise RuntimeError(f"no audio downloaded under {dest}")
    return max(candidates, key=lambda p: p.stat().st_size)


def transcribe_audio(audio: Path, video_id: str, lang: str, model: str) -> Path:
    base = lang.split("-")[0]
    result = run(
        [
            str(PYTHON),
            str(SCRIPTS / "transcribe.py"),
            str(audio),
            "--model",
            model,
            "--language",
            base,
        ],
        capture=True,
    )
    srt = ROOT / "subtitles" / f"{video_id}.{base}.srt"
    if not srt.is_file():
        # transcribe.py names the output from the audio stem; locate the newest match.
        found = sorted(
            (ROOT / "subtitles").glob(f"{video_id}*.{base}.srt"),
            key=lambda p: p.stat().st_mtime,
        )
        if not found:
            raise RuntimeError(
                f"transcription finished but no SRT found for {video_id} ({base}); "
                f"last output: {result.stdout[-500:]}"
            )
        srt = found[-1]
    target = audio.parent / "transcript.whisper.srt"
    shutil.copyfile(srt, target)
    return target


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    events: list[tuple[float, float, str]] = []
    for m in SRT_CUE.finditer(raw):
        start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000
        end = int(m.group(5)) * 3600 + int(m.group(6)) * 60 + int(m.group(7)) + int(m.group(8)) / 1000
        text = clean(" ".join(m.group(9).splitlines()))
        if text:
            events.append((start, max(end, start + 0.2), text))
    return events


def segments_from_vtt(path: Path) -> list[dict]:
    events = parse_vtt(path)
    return [
        {"start": round(start, 3), "end": round(start + max(duration, 0.2), 3), "text": clean(text)}
        for start, duration, text in events
        if clean(text)
    ]


def segments_from_srt(path: Path) -> list[dict]:
    return [
        {"start": round(start, 3), "end": round(end, 3), "text": text}
        for start, end, text in parse_srt(path)
        if text
    ]


def fmt_ts(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"


def group_paragraphs(segments: list[dict], gap: float = 2.5, max_cues: int = 12) -> list[list[dict]]:
    paragraphs: list[list[dict]] = []
    current: list[dict] = []
    for seg in segments:
        if current and (seg["start"] - current[-1]["end"] > gap or len(current) >= max_cues):
            paragraphs.append(current)
            current = []
        current.append(seg)
    if current:
        paragraphs.append(current)
    return paragraphs


def write_markdown(
    path: Path,
    *,
    title: str,
    url: str,
    channel: str,
    published: str,
    duration_s: float | None,
    language: str,
    transcript_source: str,
    retrieved: str,
    segments: list[dict],
) -> None:
    lines = [
        f"# {title}",
        "",
        f"- Source: {url}",
        f"- Channel: {channel or 'unknown'}",
        f"- Published: {published or 'unknown'}",
        f"- Duration: {duration_s:.0f}s" if duration_s else "- Duration: unknown",
        f"- Language: {language}",
        f"- Transcript: {transcript_source}",
        f"- Retrieved: {retrieved}",
        "",
        "> Original transcript from the source. Paragraph grouping and tag cleanup only;",
        "> no AI summary or rewrite. Timestamps are source cue times.",
        "",
        "## Transcript",
        "",
    ]
    for para in group_paragraphs(segments):
        text = " ".join(item["text"] for item in para).strip()
        lines.append(f"**[{fmt_ts(para[0]['start'])}]** {text}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def update_catalog(docling_root: Path, video_id: str, entry: dict) -> Path:
    catalog_path = docling_root / "output" / "catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    if catalog_path.is_file():
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            catalog = {"schema_version": 1, "sources": {}}
    else:
        catalog = {"schema_version": 1, "sources": {}}
    catalog.setdefault("schema_version", 1)
    catalog.setdefault("sources", {})
    catalog["sources"][f"youtube:{video_id}"] = entry
    catalog["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    tmp = catalog_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(catalog_path)
    return catalog_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", help="YouTube watch URL or video URL")
    ap.add_argument(
        "--docling-root",
        default=os.environ.get("DOCLING_ROOT"),
        help="Docling Bridge root (or set DOCLING_ROOT)",
    )
    ap.add_argument("--lang", default="auto", help="subtitle language; default picks the original/en")
    ap.add_argument("--whisper-model", default="medium", help="faster-whisper model when no subtitles exist")
    ap.add_argument("--no-whisper", action="store_true", help="do not fall back to local transcription")
    ap.add_argument("--force", action="store_true", help="overwrite an existing source bundle")
    args = ap.parse_args()

    if not args.docling_root:
        ap.error("--docling-root is required (or set DOCLING_ROOT)")
    if not YTDLP.is_file() or not PYTHON.is_file():
        raise SystemExit(f"YouTube-B virtualenv is not ready: {YTDLP} / {PYTHON}")

    docling_root = Path(args.docling_root).expanduser().resolve()
    info = ytdlp_json(args.url)
    video_id = str(info["id"])
    input_dir = docling_root / "input" / "youtube" / video_id
    output_dir = docling_root / "output" / "youtube" / video_id
    if output_dir.exists() and any(output_dir.iterdir()) and not args.force:
        raise SystemExit(f"source already exists: {output_dir} (use --force to overwrite)")

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "metadata.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lang, source = pick_language(info, args.lang)
    transcript_path: Path | None = None
    if source in {"manual", "auto"}:
        try:
            vtt = download_subs(args.url, video_id, lang, source, input_dir)
            segments = segments_from_vtt(vtt)
            transcript_path = vtt
        except RuntimeError as exc:
            print(f"subtitle download failed: {exc}", file=sys.stderr)
            source = None
    else:
        print(f"no subtitles for requested language ({lang})", file=sys.stderr)

    if not transcript_path and not args.no_whisper:
        print("falling back to local faster-whisper transcription", file=sys.stderr)
        audio = download_audio(args.url, video_id, input_dir)
        srt = transcribe_audio(audio, video_id, lang, args.whisper_model)
        segments = segments_from_srt(srt)
        transcript_path = srt
        source = "whisper"

    if not transcript_path:
        source_json = {
            "schema_version": 1,
            "source_id": video_id,
            "kind": "youtube",
            "url": args.url,
            "video_id": video_id,
            "title": info.get("title"),
            "channel": info.get("channel") or info.get("uploader"),
            "published": info.get("upload_date"),
            "duration_s": info.get("duration"),
            "language": lang,
            "transcript_source": None,
            "status": "blocked_no_transcript",
            "input_files": ["input/youtube/%s/metadata.json" % video_id],
            "output_files": [],
            "retrieved_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "local_only": True,
        }
        (output_dir / "source.json").write_text(
            json.dumps(source_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        update_catalog(docling_root, video_id, source_json)
        raise SystemExit("no transcript; source recorded as blocked_no_transcript")

    segments = [seg for seg in segments if seg["text"].strip()]
    if not segments:
        raise SystemExit("transcript is empty after parsing")

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    title = info.get("title") or video_id
    channel = info.get("channel") or info.get("uploader") or ""
    published = info.get("upload_date") or ""
    language = lang
    transcript_source = source or "unknown"

    (output_dir / "metadata.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "transcript.segments.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": video_id,
                "video_id": video_id,
                "language": language,
                "transcript_source": transcript_source,
                "segments": [
                    {"index": i, **seg} for i, seg in enumerate(segments, 1)
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "chapters.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": video_id,
                "source": "youtube" if info.get("chapters") else "none",
                "chapters": info.get("chapters") or [],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    write_markdown(
        output_dir / "transcript.clean.md",
        title=title,
        url=args.url,
        channel=channel,
        published=published,
        duration_s=info.get("duration"),
        language=language,
        transcript_source=transcript_source,
        retrieved=now,
        segments=segments,
    )

    input_files = ["input/youtube/%s/metadata.json" % video_id]
    if transcript_path and transcript_path.parent == input_dir:
        input_files.append(f"input/youtube/{video_id}/{transcript_path.name}")
    output_files = [
        f"output/youtube/{video_id}/transcript.clean.md",
        f"output/youtube/{video_id}/transcript.segments.json",
        f"output/youtube/{video_id}/chapters.json",
        f"output/youtube/{video_id}/metadata.json",
    ]
    source_json = {
        "schema_version": 1,
        "source_id": video_id,
        "kind": "youtube",
        "url": args.url,
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "published": published,
        "duration_s": info.get("duration"),
        "language": language,
        "transcript_source": transcript_source,
        "status": "ready",
        "input_files": input_files,
        "output_files": output_files,
        "retrieved_at": now,
        "local_only": True,
        "license_note": "YouTube source; local research use only. Check rights before reuse.",
    }
    (output_dir / "source.json").write_text(
        json.dumps(source_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    catalog = update_catalog(docling_root, video_id, source_json)

    print(f"source:   {video_id}")
    print(f"title:    {title}")
    print(f"language: {language} ({transcript_source})")
    print(f"segments: {len(segments)}")
    print(f"input:    {input_dir}")
    print(f"output:   {output_dir}")
    print(f"catalog:  {catalog}")


if __name__ == "__main__":
    main()
