from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from db_backup.config import NotificationsConfig


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

    if config.discord_webhook_url:
        try:
            _post_json(config.discord_webhook_url, {"content": message})
            logging.info("Discord notification sent")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            logging.warning("Discord notification failed: %s", exc)

    if config.telegram_bot_token and config.telegram_chat_id:
        telegram_url = (
            f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        )
        try:
            _post_json(
                telegram_url,
                {
                    "chat_id": config.telegram_chat_id,
                    "text": message,
                },
            )
            logging.info("Telegram notification sent")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            logging.warning("Telegram notification failed: %s", exc)
