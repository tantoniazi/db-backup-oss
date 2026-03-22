from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from db_backup.config import NotificationsConfig


def _is_unresolved_placeholder(value: str) -> bool:
    return bool(re.fullmatch(r"\$\{[^}]+\}", value.strip()))


def _is_http_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _post_json(url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10):
        return None


def send_notifications(config: NotificationsConfig, message: str) -> None:
    if not config.enabled:
        return

    discord_url = config.discord_webhook_url.strip()
    if discord_url and not _is_unresolved_placeholder(discord_url):
        if not _is_http_url(discord_url):
            logging.warning("Discord notification skipped: invalid webhook URL format")
        else:
            try:
                _post_json(discord_url, {"content": message})
                logging.info("Discord notification sent")
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                logging.warning("Discord notification failed: %s", exc)

    telegram_token = config.telegram_bot_token.strip()
    telegram_chat_id = config.telegram_chat_id.strip()
    token_valid = telegram_token and not _is_unresolved_placeholder(telegram_token)
    chat_valid = telegram_chat_id and not _is_unresolved_placeholder(telegram_chat_id)
    if token_valid and chat_valid:
        telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        try:
            _post_json(
                telegram_url,
                {
                    "chat_id": telegram_chat_id,
                    "text": message,
                },
            )
            logging.info("Telegram notification sent")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            logging.warning("Telegram notification failed: %s", exc)
