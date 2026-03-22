from __future__ import annotations

from pathlib import Path

from db_backup.retention import RemoteObject


class NoopProvider:
    """Provider that disables remote upload but keeps extension points stable."""

    def upload_file(self, local_path: Path, remote_key: str) -> None:
        return None

    def list_objects(self, prefix: str) -> list[RemoteObject]:
        return []

    def delete_object(self, key: str) -> None:
        return None
