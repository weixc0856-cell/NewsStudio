"""Dynamic audio ducking for dubbed intros -- FFmpeg sidechaincompress only.

The dub track (Chinese narration) drives the sidechain: while it speaks, the
original English audio is compressed to roughly 15%, then recovers smoothly.
No external mixing library is used.

Usage (standalone, re-mix an already rendered clip):
    uv run python scripts/dub_mix.py --video clips/<id>/clip-01.mp4 \
        --dub dub/<id>/track.wav --ass clips/<id>/work/clip-01.ass \
        --out clips/<id>/final/clip-01.dub.mp4 --verify

The same filter chain is reused by auto_clip.py when --dub-dir is given.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS: dict[str, Any] = {
    "sample_rate": 48000,
    "duck_threshold": None,          # None -> auto-calibrated from the dub level
    "duck_target_db": -19.5,         # calibrated so measured duck ≈ 16 dB (~15% left)
    "duck_ratio": 20.0,
    "attack_ms": 15,
    "release_ms": 400,
    "dub_gain": None,                # None -> auto-normalize the narration
    "dub_target_db": -20.0,          # narration target mean level
    "qsv_quality": 19,
    "audio_bitrate": "160k",
    "min_duck_db": 12.0,
    "max_gap_delta_db": 1.5,
}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (ROOT / p)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def escape_filter_path(path: Path) -> str:
    """Escape a subtitle path for use inside an ffmpeg filter argument.

    Prefer a ROOT-relative POSIX path: ffmpeg's filter parser treats ':' as an
    option separator, and a Windows drive letter breaks the ass filter.
    """
    resolved = path.resolve()
    try:
        text = resolved.relative_to(ROOT).as_posix()
    except ValueError:
        text = resolved.as_posix().replace(":", "\\:")
    return text.replace("'", "\\'")


def _audio_chain(sample_rate: int) -> str:
    return f"aresample={sample_rate},aformat=sample_fmts=fltp:channel_layouts=stereo"


def _compress(sample_rate: int, cfg: dict[str, Any]) -> str:
    """[orig] + [dub_side] -> [ducked]."""
    threshold = cfg.get("duck_threshold")
    threshold = 0.05 if threshold is None else float(threshold)
    comp = (f"sidechaincompress=threshold={threshold:.6f}"
            f":ratio={float(cfg['duck_ratio']):.1f}"
            f":attack={int(cfg['attack_ms'])}:release={int(cfg['release_ms'])}"
            f":makeup=1[ducked]")
    return f"[orig][dub_side]{comp}"


def build_filter_complex(ass: Path | None = None,
                         cfg: dict[str, Any] | None = None) -> str:
    """Return the filter_complex graph: [0:v] -> [v], audio mix -> [aout].

    [0:a] ----------------------> [orig]
    [1:a] -> volume -> asplit -> [dub_side], [dub_mix]
    [orig][dub_side] sidechaincompress -> [ducked]   (English ducks ~15%)
    [ducked][dub_mix] amix -> [aout]                 (dub on top)
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    sr = int(cfg["sample_rate"])
    chain = _audio_chain(sr)
    parts = []
    if ass is not None:
        parts.append(f"[0:v]ass={escape_filter_path(ass)}[v]")
    parts += [
        f"[0:a]{chain}[orig]",
        f"[1:a]{chain},volume={float(cfg.get('dub_gain') or 1.0):.3f},apad[dub]",
        "[dub]asplit=2[dub_side][dub_mix]",
        _compress(sr, cfg),
        "[ducked][dub_mix]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.95[aout]",
    ]
    return ";".join(parts)


def build_bed_filter(cfg: dict[str, Any] | None = None) -> str:
    """Same compressor, but only the ducked original is emitted ([ducked]).

    Used for acceptance: comparing the ducked bed against the original proves
    the ducking depth without the narration masking the measurement.
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    sr = int(cfg["sample_rate"])
    chain = _audio_chain(sr)
    return ";".join([
        f"[0:a]{chain}[orig]",
        f"[1:a]{chain},volume={float(cfg.get('dub_gain') or 1.0):.3f},apad[dub_side]",
        _compress(sr, cfg),
    ])


def build_ffmpeg_cmd(video: Path, dub: Path, out: Path, ass: Path | None = None,
                     cfg: dict[str, Any] | None = None, *,
                     start_s: float | None = None, length_s: float | None = None,
                     fps: str | None = None, cfr: bool = False) -> list[str]:
    cfg = {**DEFAULTS, **(cfg or {})}
    cfg["dub_gain"] = resolve_gain(dub, cfg)
    cfg["duck_threshold"] = resolve_threshold(dub, cfg)
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    if start_s is not None:
        cmd += ["-ss", f"{start_s:.3f}"]
    cmd += ["-i", str(video), "-i", str(dub)]
    if length_s is not None:
        cmd += ["-t", f"{length_s:.3f}"]
    cmd += ["-map_chapters", "-1",
            "-filter_complex", build_filter_complex(ass, cfg),
            "-map", "[v]" if ass is not None else "0:v:0",
            "-map", "[aout]",
            "-c:v", "h264_qsv", "-global_quality:v", str(cfg["qsv_quality"]), "-preset", "slow",
            "-c:a", "aac", "-b:a", cfg["audio_bitrate"], "-ar", str(cfg["sample_rate"]),
            "-sn", "-dn", "-movflags", "+faststart", "-avoid_negative_ts", "make_zero"]
    if cfr and fps:
        cmd += ["-fps_mode", "cfr", "-r", fps]
    cmd.append(str(out))
    return cmd


def run_cmd(cmd: list[str], timeout: int = 7200) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=str(ROOT))


def probe_duration(path: Path) -> float:
    proc = run_cmd(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "csv=p=0", str(path)], timeout=60)
    return float(proc.stdout.strip() or 0)


def measure_volume(path: Path, start_s: float, length_s: float) -> float | None:
    """Mean volume (dBFS, NaN -> None) of an audio slice."""
    proc = run_cmd([
        "ffmpeg", "-hide_banner", "-ss", f"{max(start_s, 0):.3f}",
        "-t", f"{max(length_s, 0.05):.3f}", "-i", str(path),
        "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-",
    ], timeout=300)
    match = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", proc.stderr)
    if not match:
        return None
    value = match.group(1)
    return None if value == "-inf" else float(value)


def mean_volume_db(path: Path) -> float | None:
    """Mean volume (dBFS) of a whole audio file."""
    proc = run_cmd([
        "ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:a:0",
        "-af", "volumedetect", "-f", "null", "-",
    ], timeout=600)
    match = re.search(r"mean_volume:\s*(-?[\d.]+) dB", proc.stderr)
    return float(match.group(1)) if match else None


def resolve_gain(dub: Path, cfg: dict[str, Any] | None = None) -> float:
    """Normalize arbitrary reference loudness to a consistent narration level."""
    cfg = {**DEFAULTS, **(cfg or {})}
    if cfg.get("dub_gain") is not None:
        return float(cfg["dub_gain"])
    level = mean_volume_db(dub)
    if level is None:
        return 1.0
    gain = 10 ** ((float(cfg["dub_target_db"]) - level) / 20)
    return float(min(max(gain, 0.25), 4.0))


def resolve_threshold(dub: Path, cfg: dict[str, Any] | None = None) -> float:
    """Pick the compressor threshold that lands the duck at ~duck_target_db.

    attenuation = (sidechain_level_db - threshold_db) * (1 - 1/ratio)
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    if cfg.get("duck_threshold") is not None:
        return float(cfg["duck_threshold"])
    level = mean_volume_db(dub)
    if level is None:
        return 0.05
    level += 20 * math.log10(max(resolve_gain(dub, cfg), 1e-6))
    ratio = max(float(cfg["duck_ratio"]), 1.01)
    target = abs(float(cfg["duck_target_db"]))
    threshold_db = level - target / (1 - 1 / ratio)
    return float(10 ** (threshold_db / 20))


def render_ducked_bed(video: Path, dub: Path, out: Path, cfg: dict[str, Any] | None = None,
                      start_s: float | None = None, length_s: float | None = None) -> Path:
    cfg = {**DEFAULTS, **(cfg or {})}
    cfg["dub_gain"] = resolve_gain(dub, cfg)
    cfg["duck_threshold"] = resolve_threshold(dub, cfg)
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    if start_s is not None:
        cmd += ["-ss", f"{start_s:.3f}"]
    cmd += ["-i", str(video), "-i", str(dub)]
    if length_s is not None:
        cmd += ["-t", f"{length_s:.3f}"]
    cmd += ["-filter_complex", build_bed_filter(cfg), "-map", "[ducked]",
            "-c:a", "pcm_s16le", "-ar", str(cfg["sample_rate"]), str(out)]
    proc = run_cmd(cmd, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"bed render failed: {proc.stderr.strip()[-400:]}")
    return out


def verify_ducking(video: Path, dub: Path, dub_windows: list[tuple[float, float]],
                   gap_windows: list[tuple[float, float]], cfg: dict[str, Any] | None = None,
                   start_s: float | None = None, length_s: float | None = None) -> dict[str, Any]:
    """Measure how far the original is pushed down while the dub speaks.

    Renders the ducked bed (no narration mixed in) and compares it to the
    original track over the same windows.
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    with tempfile.TemporaryDirectory(prefix="duck-verify-") as tmp:
        bed = render_ducked_bed(video, dub, Path(tmp) / "bed.wav", cfg, start_s, length_s)
        offset = -start_s if start_s else 0.0
        rows = []
        for label, windows in (("dub", dub_windows), ("gap", gap_windows)):
            for begin, length in windows:
                orig_db = measure_volume(video, begin, length)
                bed_db = measure_volume(bed, begin - offset, length)
                delta = None if orig_db is None or bed_db is None else orig_db - bed_db
                rows.append({"kind": label, "start": round(begin, 2), "length": round(length, 2),
                             "original_db": orig_db, "bed_db": bed_db,
                             "duck_db": None if delta is None else round(delta, 2)})
    dub_rows = [r for r in rows if r["kind"] == "dub" and r["duck_db"] is not None]
    gap_rows = [r for r in rows if r["kind"] == "gap" and r["duck_db"] is not None]
    duck_values = [r["duck_db"] for r in dub_rows]
    gap_values = [abs(r["duck_db"]) for r in gap_rows]
    passed = bool(duck_values) and min(duck_values) >= float(cfg["min_duck_db"])
    if gap_values:
        passed = passed and max(gap_values) <= float(cfg["max_gap_delta_db"])
    return {
        "passed": passed,
        "min_duck_db": min(duck_values) if duck_values else None,
        "max_gap_delta_db": max(gap_values) if gap_values else None,
        "windows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Mix dubbed narration with sidechain ducking")
    ap.add_argument("--video", required=True)
    ap.add_argument("--dub", required=True)
    ap.add_argument("--ass", default=None, help="ASS subtitle to burn in the same pass")
    ap.add_argument("--out", required=True)
    ap.add_argument("--qsv-quality", type=int, default=DEFAULTS["qsv_quality"])
    ap.add_argument("--audio-bitrate", default=DEFAULTS["audio_bitrate"])
    ap.add_argument("--duck-threshold", type=float, default=DEFAULTS["duck_threshold"])
    ap.add_argument("--duck-target-db", type=float, default=DEFAULTS["duck_target_db"],
                    help="auto-calibration target attenuation in dB (-16.5 ≈ 15%% leftover)")
    ap.add_argument("--duck-ratio", type=float, default=DEFAULTS["duck_ratio"])
    ap.add_argument("--attack-ms", type=int, default=DEFAULTS["attack_ms"])
    ap.add_argument("--release-ms", type=int, default=DEFAULTS["release_ms"])
    ap.add_argument("--dub-gain", type=float, default=None,
                    help="fixed narration gain; default: auto-normalize to --dub-target-db")
    ap.add_argument("--dub-target-db", type=float, default=DEFAULTS["dub_target_db"])
    ap.add_argument("--verify", action="store_true",
                    help="after mixing, measure ducking depth over the dub's speech windows")
    ap.add_argument("--dub-window", action="append", default=[], metavar="START:LENGTH",
                    help="speech window in seconds for --verify (repeatable)")
    args = ap.parse_args()

    video, dub, out = resolve(args.video), resolve(args.dub), resolve(args.out)
    ass = resolve(args.ass) if args.ass else None
    for path, label in ((video, "video"), (dub, "dub")):
        if not path.exists():
            print(f"{label} not found: {path}", file=sys.stderr)
            return 2
    out.parent.mkdir(parents=True, exist_ok=True)

    cfg = {"qsv_quality": args.qsv_quality, "audio_bitrate": args.audio_bitrate,
           "duck_threshold": args.duck_threshold, "duck_ratio": args.duck_ratio,
           "duck_target_db": args.duck_target_db,
           "attack_ms": args.attack_ms, "release_ms": args.release_ms,
           "dub_gain": args.dub_gain, "dub_target_db": args.dub_target_db}
    out_tmp = out.with_suffix(".tmp.mp4")
    cmd = build_ffmpeg_cmd(video, dub, out_tmp, ass, cfg)
    print("ffmpeg: " + " ".join(cmd), flush=True)
    proc = run_cmd(cmd)
    if proc.returncode != 0:
        print(proc.stderr.strip()[-1200:], file=sys.stderr)
        return 1
    out_tmp.replace(out)

    report: dict[str, Any] = {"out": rel(out), "size_bytes": out.stat().st_size,
                              "duration_s": round(probe_duration(out), 3)}
    if args.verify:
        windows = []
        for spec in args.dub_window:
            begin, _, length = spec.partition(":")
            windows.append((float(begin), float(length or 1.0)))
        dub_len = probe_duration(dub)
        gap_begin = dub_len + 0.4
        gap_len = max(0.0, min(3.0, report["duration_s"] - gap_begin))
        gaps = [(gap_begin, gap_len)] if gap_len > 0.2 else []
        report["ducking"] = verify_ducking(video, dub, windows, gaps, cfg)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ducking"]["passed"] else 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
