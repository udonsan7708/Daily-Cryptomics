"""File system helpers for the Daily Cryptomics agent."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def ensure_output_dir(base_dir: Path) -> Path:
    """Create and return a dated output sub-directory (YYYY-MM-DD)."""
    dated = base_dir / datetime.utcnow().strftime("%Y-%m-%d")
    dated.mkdir(parents=True, exist_ok=True)
    return dated


def save_text(text: str, path: Path) -> Path:
    """Write *text* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def copy_file(src: Path, dest: Path) -> Path:
    """Copy *src* to *dest*, creating parent directories as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def run_id(prefix: str = "") -> str:
    """Return a timestamp-based unique run identifier."""
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}{stamp}" if prefix else stamp
