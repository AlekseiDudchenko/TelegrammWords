"""Minimal Telegram Bot API client: send a message and its voice reply."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
TIMEOUT = 30.0
RETRIES = 3


class TelegramError(RuntimeError):
    pass


def send_message(token: str, chat_id: str, text: str) -> int:
    """Send the message and return its message_id."""
    url = f"{API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    return _post(url, json=payload)


def send_voice(
    token: str,
    chat_id: str,
    path: Path,
    reply_to: int | None = None,
    caption: str | None = None,
) -> int:
    """Upload an OGG Opus file as a voice message, optionally as a reply."""
    url = f"{API_BASE}/bot{token}/sendVoice"
    data = {"chat_id": chat_id, "disable_notification": "true"}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"
    if reply_to is not None:
        data["reply_parameters"] = json.dumps({"message_id": reply_to})
    content = path.read_bytes()
    return _post(url, data=data, files={"voice": (path.name, content, "audio/ogg")})


def _post(url: str, **request) -> int:
    """POST to the Bot API and return the resulting message_id.

    Network errors and 5xx are retried with growing backoff; a 4xx is a
    configuration or formatting mistake and is reported immediately.
    """
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            response = httpx.post(url, timeout=TIMEOUT, **request)
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
