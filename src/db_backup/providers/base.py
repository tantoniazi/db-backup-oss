from __future__ import annotations

from pathlib import Path
from typing import Protocol

from db_backup.retention import RemoteObject


class StorageProvider(Protocol):
    def upload_file(self, local_path: Path, remote_key: str) -> None:
        ...

    def list_objects(self, prefix: str) -> list[RemoteObject]:
        ...

    def delete_object(self, key: str) -> None:
        ...
