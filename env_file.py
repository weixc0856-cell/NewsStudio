"""Load the repo-root ``.env`` into ``os.environ``.

The repository must stay safe to push to a remote: no machine-specific paths
or keys live in tracked files.  Real values live in ``.env`` (gitignored);
``.env.example`` documents every supported key.

Usage: importing this module loads the file once, without overriding variables
that are already set in the environment::

    import env_file  # noqa: F401

Scripts under ``scripts/`` need the repo root on ``sys.path`` first::

    sys.path.insert(0, str(ROOT))
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"


def parse_env_text(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines; ignores blanks, ``#`` comments and ``export``."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env(path: str | Path | None = None, *, override: bool = False) -> dict[str, str]:
    """Load a dotenv file into ``os.environ`` and return the parsed values."""
    env_path = Path(path) if path is not None else ENV_FILE
    if not env_path.is_file():
        return {}
    values = parse_env_text(env_path.read_text(encoding="utf-8", errors="replace"))
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values


load_env()
