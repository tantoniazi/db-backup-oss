from __future__ import annotations

import argparse
import logging
from pathlib import Path

from db_backup.backup import create_compressed_backup
from db_backup.config import load_config
from db_backup.notifier import send_notifications
from db_backup.providers import build_provider
from db_backup.retention import prune_local_backups, prune_remote_backups
from db_backup.setup_wizard import run_setup_wizard


def _build_remote_key(prefix: str, engine: str, db_name: str, file_name: str) -> str:
    clean_prefix = prefix.strip("/")
    parts = [clean_prefix, engine, db_name, file_name] if clean_prefix else [engine, db_name, file_name]
    return "/".join(parts)


def run(config_path: Path) -> None:
    config = load_config(config_path)
    logging.info("Starting backup for %s database '%s'", config.database.engine, config.database.name)
    try:
        backup_path = create_compressed_backup(config.database, config.backup.output_root)
        logging.info("Local backup created: %s", backup_path)

        engine_folder = config.backup.output_root / config.database.engine
        removed_local = prune_local_backups(
            folder=engine_folder,
            db_name=config.database.name,
            keep=config.backup.local_keep,
        )
        if removed_local:
            logging.info("Local retention removed %d file(s)", len(removed_local))

        provider = build_provider(config.storage)
        remote_key = _build_remote_key(
            prefix=config.storage.prefix,
            engine=config.database.engine,
            db_name=config.database.name,
            file_name=backup_path.name,
        )

        provider.upload_file(backup_path, remote_key)
        logging.info("Remote upload finished: %s", remote_key)

        remote_prefix = _build_remote_key(
            prefix=config.storage.prefix,
            engine=config.database.engine,
            db_name=config.database.name,
            file_name="",
        ).rstrip("/")

        remote_objects = provider.list_objects(remote_prefix)
        to_delete = prune_remote_backups(remote_objects, keep=config.storage.keep_remote)
        for item in to_delete:
            provider.delete_object(item.key)

        if to_delete:
            logging.info("Remote retention removed %d object(s)", len(to_delete))

        send_notifications(
            config.notifications,
            (
                "Backup finished successfully\n"
                f"Database: {config.database.engine}/{config.database.name}\n"
                f"File: {backup_path.name}\n"
                f"Remote key: {remote_key}"
            ),
        )
        logging.info("Backup workflow completed")
    except Exception as exc:
        send_notifications(
            config.notifications,
            (
                "Backup failed\n"
                f"Database: {config.database.engine}/{config.database.name}\n"
                f"Error: {exc}"
            ),
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="db-backup",
        description="Backup MySQL/PostgreSQL database and upload to S3-compatible storage",
    )
    parser.add_argument(
        "--config",
        default="./config/config.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Run interactive setup wizard and write config file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config_path = Path(args.config)

    if args.wizard:
        run_setup_wizard(config_path)
        return

    run(config_path)


if __name__ == "__main__":
    main()
