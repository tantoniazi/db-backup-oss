from __future__ import annotations

from pathlib import Path
import time

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from db_backup.config import StorageConfig
from db_backup.retention import RemoteObject


class S3Provider:
    def __init__(self, config: StorageConfig) -> None:
        if not config.bucket:
            raise ValueError("storage.bucket is required for provider=s3")
        self._bucket = config.bucket
        self._max_attempts = 4
        client_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 8, "mode": "standard"},
            connect_timeout=10,
            read_timeout=60,
        )
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url or None,
            region_name=config.region,
            aws_access_key_id=config.access_key_id or None,
            aws_secret_access_key=config.secret_access_key or None,
            config=client_config,
        )

    def _retry(self, operation_name: str, fn):
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return fn()
            except (BotoCoreError, ClientError, OSError) as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    break
                sleep_seconds = 2 ** (attempt - 1)
                time.sleep(sleep_seconds)
        raise RuntimeError(f"S3 operation '{operation_name}' failed after retries: {last_error}")

    def _ensure_remote_prefixes(self, remote_key: str) -> None:
        parts = [p for p in remote_key.split("/") if p]
        if len(parts) <= 1:
            return

        current: list[str] = []
        for segment in parts[:-1]:
            current.append(segment)
            folder_key = "/".join(current) + "/"
            self._retry(
                "create_prefix",
                lambda folder_key=folder_key: self._client.put_object(
                    Bucket=self._bucket,
                    Key=folder_key,
                    Body=b"",
                ),
            )

    def upload_file(self, local_path: Path, remote_key: str) -> None:
        self._ensure_remote_prefixes(remote_key)
        self._retry(
            "upload_file",
            lambda: self._client.upload_file(str(local_path), self._bucket, remote_key),
        )

    def list_objects(self, prefix: str) -> list[RemoteObject]:
        paginator = self._client.get_paginator("list_objects_v2")
        pages = self._retry(
            "list_objects_v2",
            lambda: paginator.paginate(Bucket=self._bucket, Prefix=prefix),
        )
        objects: list[RemoteObject] = []

        for page in pages:
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.endswith("/"):
                    continue
                objects.append(
                    RemoteObject(
                        key=key,
                        last_modified=item["LastModified"],
                    )
                )

        return objects

    def delete_object(self, key: str) -> None:
        self._retry(
            "delete_object",
            lambda: self._client.delete_object(Bucket=self._bucket, Key=key),
        )
