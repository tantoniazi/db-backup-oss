from __future__ import annotations

from pathlib import Path

import boto3

from db_backup.config import StorageConfig
from db_backup.retention import RemoteObject


class S3Provider:
    def __init__(self, config: StorageConfig) -> None:
        if not config.bucket:
            raise ValueError("storage.bucket is required for provider=s3")
        self._bucket = config.bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url or None,
            region_name=config.region,
            aws_access_key_id=config.access_key_id or None,
            aws_secret_access_key=config.secret_access_key or None,
        )

    def upload_file(self, local_path: Path, remote_key: str) -> None:
        self._client.upload_file(str(local_path), self._bucket, remote_key)

    def list_objects(self, prefix: str) -> list[RemoteObject]:
        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self._bucket, Prefix=prefix)
        objects: list[RemoteObject] = []

        for page in pages:
            for item in page.get("Contents", []):
                objects.append(
                    RemoteObject(
                        key=item["Key"],
                        last_modified=item["LastModified"],
                    )
                )

        return objects

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
