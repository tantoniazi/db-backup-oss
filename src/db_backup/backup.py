from __future__ import annotations

import gzip
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from db_backup.config import DatabaseConfig


def _resolve_mysql_dump_binary() -> str:
    # Prefer mysqldump for compatibility, but MariaDB now recommends mariadb-dump.
    if shutil.which("mysqldump"):
        return "mysqldump"
    if shutil.which("mariadb-dump"):
        return "mariadb-dump"
    return "mysqldump"


def _dump_command(db: DatabaseConfig) -> tuple[list[str], dict[str, str]]:
    env = os.environ.copy()
    if db.engine == "mysql":
        env["MYSQL_PWD"] = db.password
        mysql_dump_bin = _resolve_mysql_dump_binary()
        command = [
            mysql_dump_bin,
            "--single-transaction",
            "--quick",
            "--routines",
            "--triggers",
            "-h",
            db.host,
            "-P",
            str(db.port),
            "-u",
            db.user,
            db.name,
        ]
    else:
        env["PGPASSWORD"] = db.password
        command = [
            "pg_dump",
            "-h",
            db.host,
            "-p",
            str(db.port),
            "-U",
            db.user,
            "-d",
            db.name,
            "-F",
            "p",
        ]

    if db.extra_args:
        command.extend(db.extra_args)

    return command, env


def _humanize_dump_error(db: DatabaseConfig, return_code: int, stderr_text: str) -> str:
    if db.engine == "mysql":
        if "1698" in stderr_text or "Access denied" in stderr_text:
            return (
                "MySQL authentication failed. Check database.user/database.password and grants. "
                "On MariaDB, root may use unix_socket auth; create a dedicated user for backups or "
                "configure proper authentication for TCP host/port. "
                f"Original error: {stderr_text}"
            )
        if re.search(r"not found|No such file", stderr_text, flags=re.IGNORECASE):
            return (
                "MySQL dump tool not available. Install mysql-client or mariadb-client. "
                f"Original error: {stderr_text}"
            )

    if db.engine == "postgres":
        if "password authentication failed" in stderr_text.lower():
            return (
                "PostgreSQL authentication failed. Check database.user/database.password and pg_hba.conf rules. "
                f"Original error: {stderr_text}"
            )

    return f"Backup command failed with code {return_code}: {stderr_text}"


def create_compressed_backup(db: DatabaseConfig, output_root: Path) -> Path:
    engine_dir = output_root / db.engine
    engine_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    file_name = f"{db.name}_{timestamp}.sql.gz"
    output_path = engine_dir / file_name

    command, env = _dump_command(db)

    if shutil.which(command[0]) is None:
        raise RuntimeError(
            f"Dependency '{command[0]}' not found. Install database client tools first."
        )

    with output_path.open("wb") as raw_file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, compresslevel=6) as gz_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            assert process.stdout is not None
            shutil.copyfileobj(process.stdout, gz_file)
            process.stdout.close()
            stderr_bytes = process.stderr.read() if process.stderr else b""
            return_code = process.wait()

    if return_code != 0:
        output_path.unlink(missing_ok=True)
        stderr_text = stderr_bytes.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(_humanize_dump_error(db, return_code, stderr_text))

    return output_path
