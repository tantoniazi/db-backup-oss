from __future__ import annotations

from importlib import import_module

from db_backup.config import StorageConfig
from db_backup.providers.base import StorageProvider
from db_backup.providers.noop_provider import NoopProvider
from db_backup.providers.s3_provider import S3Provider


def _load_class_from_path(dotted_path: str):
    module_name, _, class_name = dotted_path.rpartition(".")
    if not module_name or not class_name:
        raise ValueError(
            "Invalid provider path. Use e.g. 'my_package.my_module.MyProvider'"
        )
    module = import_module(module_name)
    return getattr(module, class_name)


def build_provider(config: StorageConfig) -> StorageProvider:
    provider_name = config.provider.lower()

    if provider_name == "s3":
        return S3Provider(config)
    if provider_name == "noop":
        return NoopProvider()

    provider_class = _load_class_from_path(config.provider)
    provider = provider_class(config)

    for method_name in ("upload_file", "list_objects", "delete_object"):
        if not hasattr(provider, method_name):
            raise TypeError(
                f"Custom provider '{config.provider}' must implement '{method_name}'"
            )

    return provider
