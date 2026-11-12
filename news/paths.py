"""Repo vs output-root separation.

The repository may be pushed to a remote; rendered media, screenshots, voice
files and transcripts must not be.  Follow the same split as Local-Drama-Studio:
code/config/docs/tests are tracked, every production artifact goes to
``NEWS_OUTPUT_ROOT``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import env_file  # noqa: E402,F401  # 载入仓库根 .env（本机路径/密钥不进 Git）

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "output"


def output_root() -> Path:
    raw = os.environ.get("NEWS_OUTPUT_ROOT")
    root = Path(raw).expanduser() if raw else DEFAULT_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def episode_dir(episode_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in episode_id)
    if not safe:
        raise ValueError("episode id is empty")
    root = output_root() / "episodes" / safe
    for name in ("assets", "voice", "work", "out", "capture"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def resolve_out(raw: str | Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = output_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
