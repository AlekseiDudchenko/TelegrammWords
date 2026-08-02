"""Minimal Telegram Bot API client: send one message."""

from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
TIMEOUT = 30.0
RETRIES = 3


class TelegramError(RuntimeError):
    pass


def send_message(token: str, chat_id: str, text: str) -> int:
    """Send the message and return its message_id.

    Network errors and 5xx are retried with growing backoff; a 4xx is a
    configuration or formatting mistake and is reported immediately.
    """
    url = f"{API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            response = httpx.post(url, json=payload, timeout=TIMEOUT)
        except httpx.HTTPError as exc:
            last_error = exc
            log.warning("Telegram attempt %d failed: %s", attempt, exc)
        else:
            if response.status_code < 400:
                body = response.json()
                if not body.get("ok"):
                    raise TelegramError(f"Telegram reported an error: {body}")
                return int(body["result"]["message_id"])
            if response.status_code < 500:
                raise TelegramError(f"Telegram {response.status_code}: {response.text}")
            last_error = TelegramError(
                f"Telegram {response.status_code}: {response.text}"
            )
            log.warning("Telegram attempt %d: %s", attempt, last_error)

        if attempt < RETRIES:
            time.sleep(2**attempt)

    raise TelegramError(f"sending failed after {RETRIES} attempts: {last_error}")
