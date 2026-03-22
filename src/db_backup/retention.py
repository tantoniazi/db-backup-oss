from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RemoteObject:
    key: str
    last_modified: datetime


def prune_local_backups(folder: Path, db_name: str, keep: int) -> list[Path]:
    if keep < 1:
        raise ValueError("backup.local_keep must be >= 1")

    pattern = f"{db_name}_*.sql.gz"
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    removed: list[Path] = []

    for old_file in files[keep:]:
        old_file.unlink(missing_ok=True)
        removed.append(old_file)

    return removed


def prune_remote_backups(objects: list[RemoteObject], keep: int) -> list[RemoteObject]:
    if keep < 1:
        raise ValueError("storage.keep_remote must be >= 1")

    ordered = sorted(objects, key=lambda obj: obj.last_modified, reverse=True)
    return ordered[keep:]
