"""Guard: nothing pushed to the remote may contain a machine-specific path,
and no shippable file may be a large binary/media blob.

The repository is public-facing; real paths and keys belong in ``.env`` only.
This test walks every file that could ship (tracked plus uncommitted,
non-ignored files) and fails on:

* Windows drive-letter paths (a letter, a colon, then a slash of either kind)
* POSIX home paths (``/Users/<name>`` or ``/home/<name>``)
* UNC shares (two leading backslashes, host, share)

Placeholders are fine: ``<repo-root>``, ``<path-to-model.gguf>``,
``$NEWS_OUTPUT_ROOT``, relative paths, URLs.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BS = chr(92)
DRIVE_PATH = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z]:" + "[" + BS + BS + "/](?!" + BS + BS + "/)")
POSIX_HOME = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[A-Za-z0-9._-]+/")
UNC_PATH = re.compile(BS + BS + BS + BS + r"[A-Za-z0-9._-]+" + BS + BS + r"[A-Za-z0-9$._-]+")

SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2",
                 ".ttf", ".otf", ".mp3", ".wav", ".mp4", ".mkv", ".zip", ".pdf"}


def tracked_files() -> list[Path]:
    """Tracked files plus untracked-but-not-ignored ones (i.e. what could ship)."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others",
                              "--exclude-standard"], cwd=ROOT,
                             capture_output=True, check=True).stdout
        return [ROOT / p.decode("utf-8", "replace") for p in out.split(b"\0") if p]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", ".venv", "output", "downloads", "clips", ".runtime", "__pycache__"}
        return [p for p in ROOT.rglob("*")
                if p.is_file() and not skip.intersection(p.relative_to(ROOT).parts)]


def scan(path: Path) -> list[tuple[int, str, str]]:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return []
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    if b"\0" in raw[:4096]:
        return []
    text = raw.decode("utf-8", "ignore")
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, pattern in (("drive", DRIVE_PATH),
                              ("home", POSIX_HOME),
                              ("unc", UNC_PATH)):
            match = pattern.search(line)
            if match:
                hits.append((lineno, name, match.group(0)))
    return hits


class NoLocalPathsTest(unittest.TestCase):
    def test_tracked_files_have_no_absolute_paths(self) -> None:
        findings: list[str] = []
        for path in tracked_files():
            rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
            if rel.startswith((".venv/", "clips/")):
                continue
            for lineno, kind, sample in scan(path):
                findings.append(f"{rel}:{lineno}: {kind} path {sample!r}")
        self.assertEqual(
            [], findings,
            "Tracked files contain machine-specific paths; move them to .env "
            "(template: .env.example):\n  " + "\n  ".join(findings))


MAX_SHIPPABLE_BYTES = 2 * 1024 * 1024


class RepoSizeTest(unittest.TestCase):
    def test_shippable_files_stay_small(self) -> None:
        """Media and raw intermediates never ship; 2 MiB is the ceiling."""
        oversized: list[str] = []
        for path in tracked_files():
            rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
            if rel.startswith((".venv/", "clips/")):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_SHIPPABLE_BYTES:
                oversized.append(f"{rel}: {size / 1048576:.1f} MB")
        self.assertEqual(
            [], oversized,
            "Files larger than 2 MiB must stay out of the remote; move them to "
            "NEWS_OUTPUT_ROOT or add a .gitignore rule:\n  " + "\n  ".join(oversized))


if __name__ == "__main__":
    unittest.main()
