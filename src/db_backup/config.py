from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DatabaseConfig:
    engine: str
    host: str
    port: int
    name: str
    user: str
    password: str
    extra_args: list[str] = field(default_factory=list)


@dataclass
class BackupConfig:
    output_root: Path
    local_keep: int = 2


@dataclass
class StorageConfig:
    provider: str = "noop"
    keep_remote: int = 3
    bucket: str = ""
    prefix: str = "db-backups"
    endpoint_url: str = ""
    region: str = "us-east-1"
    access_key_id: str = ""
    secret_access_key: str = ""


@dataclass
class NotificationsConfig:
    enabled: bool = False
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@dataclass
class AppConfig:
    database: DatabaseConfig
    backup: BackupConfig
    storage: StorageConfig
    notifications: NotificationsConfig


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    expanded = _expand_env(raw)

    db_raw = expanded.get("database", {})
    backup_raw = expanded.get("backup", {})
    storage_raw = expanded.get("storage", {})
    notifications_raw = expanded.get("notifications", {})

    database = DatabaseConfig(
        engine=str(db_raw.get("engine", "")).strip().lower(),
        host=str(db_raw.get("host", "127.0.0.1")),
        port=int(db_raw.get("port", 0)),
        name=str(db_raw.get("name", "")),
        user=str(db_raw.get("user", "")),
        password=str(db_raw.get("password", "")),
        extra_args=list(db_raw.get("extra_args", [])),
    )

    if database.engine not in {"mysql", "postgres"}:
        raise ValueError("database.engine must be 'mysql' or 'postgres'")

    if database.port == 0:
        database.port = 3306 if database.engine == "mysql" else 5432

    if not database.name:
        raise ValueError("database.name is required")

    backup = BackupConfig(
        output_root=Path(str(backup_raw.get("output_root", "./backups"))),
        local_keep=int(backup_raw.get("local_keep", 2)),
    )

    storage = StorageConfig(
        provider=str(storage_raw.get("provider", "noop")).strip(),
        keep_remote=int(storage_raw.get("keep_remote", 3)),
        bucket=str(storage_raw.get("bucket", "")),
        prefix=str(storage_raw.get("prefix", "db-backups")).strip("/"),
        endpoint_url=str(storage_raw.get("endpoint_url", "")),
        region=str(storage_raw.get("region", "us-east-1")),
        access_key_id=str(storage_raw.get("access_key_id", "")),
        secret_access_key=str(storage_raw.get("secret_access_key", "")),
    )

    notifications = NotificationsConfig(
        enabled=bool(notifications_raw.get("enabled", False)),
        discord_webhook_url=str(notifications_raw.get("discord_webhook_url", "")),
        telegram_bot_token=str(notifications_raw.get("telegram_bot_token", "")),
        telegram_chat_id=str(notifications_raw.get("telegram_chat_id", "")),
    )

    return AppConfig(
        database=database,
        backup=backup,
        storage=storage,
        notifications=notifications,
    )
