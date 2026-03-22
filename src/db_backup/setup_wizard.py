from __future__ import annotations

from pathlib import Path

import yaml


def _ask(prompt: str, default: str = "") -> str:
    label = f"{prompt} [{default}]: " if default else f"{prompt}: "
    value = input(label).strip()
    return value or default


def _ask_int(prompt: str, default: int) -> int:
    while True:
        raw = _ask(prompt, str(default))
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid integer.")


def _ask_bool(prompt: str, default: bool) -> bool:
    default_text = "y" if default else "n"
    while True:
        raw = _ask(f"{prompt} (y/n)", default_text).lower()
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer y or n.")


def run_setup_wizard(config_path: Path) -> None:
    print("=== db-backup setup wizard ===")

    engine = ""
    while engine not in {"mysql", "postgres"}:
        engine = _ask("Database engine (mysql/postgres)", "mysql").lower()

    default_port = 3306 if engine == "mysql" else 5432

    db_name = _ask("Database name", "app_db")
    db_host = _ask("Database host", "127.0.0.1")
    db_port = _ask_int("Database port", default_port)
    db_user = _ask("Database user", "root" if engine == "mysql" else "postgres")
    db_password = _ask("Database password or env ref (example: ${DB_PASSWORD})", "${DB_PASSWORD}")

    output_root = _ask("Local backup root directory", "./backups")
    local_keep = _ask_int("Keep how many local backups", 2)

    provider = _ask("Storage provider (s3/noop/custom dotted path)", "s3")
    keep_remote = _ask_int("Keep how many remote backups", 3)

    storage = {
        "provider": provider,
        "keep_remote": keep_remote,
    }

    if provider == "s3":
        storage.update(
            {
                "bucket": _ask("S3 bucket", "my-linode-bucket"),
                "prefix": _ask("S3 prefix", "db-backups"),
                "endpoint_url": _ask(
                    "S3 endpoint URL (Linode example: https://us-southeast-1.linodeobjects.com)",
                    "https://us-southeast-1.linodeobjects.com",
                ),
                "region": _ask("S3 region", "us-southeast-1"),
                "access_key_id": _ask("Access key id or env ref", "${LINODE_ACCESS_KEY}"),
                "secret_access_key": _ask("Secret access key or env ref", "${LINODE_SECRET_KEY}"),
            }
        )

    notifications_enabled = _ask_bool("Enable notifications", True)
    notifications = {
        "enabled": notifications_enabled,
        "discord_webhook_url": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
    }

    if notifications_enabled:
        if _ask_bool("Enable Discord webhook notifications", True):
            notifications["discord_webhook_url"] = _ask(
                "Discord webhook URL or env ref",
                "${DISCORD_WEBHOOK_URL}",
            )

        if _ask_bool("Enable Telegram notifications", False):
            notifications["telegram_bot_token"] = _ask(
                "Telegram bot token or env ref",
                "${TELEGRAM_BOT_TOKEN}",
            )
            notifications["telegram_chat_id"] = _ask(
                "Telegram chat id or env ref",
                "${TELEGRAM_CHAT_ID}",
            )

    config_data = {
        "database": {
            "engine": engine,
            "host": db_host,
            "port": db_port,
            "name": db_name,
            "user": db_user,
            "password": db_password,
            "extra_args": [],
        },
        "backup": {
            "output_root": output_root,
            "local_keep": local_keep,
        },
        "storage": storage,
        "notifications": notifications,
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(config_data, fh, sort_keys=False)

    print(f"Configuration written to: {config_path}")
