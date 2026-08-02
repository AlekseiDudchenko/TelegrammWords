"""Minimaler Telegram-Bot-API-Client: eine Nachricht senden."""

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
    """Sendet die Nachricht und gibt die message_id zurück.

    Netzwerkfehler und 5xx werden mit wachsender Wartezeit wiederholt; ein 4xx
    ist ein Konfigurations- oder Formatfehler und wird sofort gemeldet.
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
            log.warning("Telegram-Versuch %d fehlgeschlagen: %s", attempt, exc)
        else:
            if response.status_code < 400:
                body = response.json()
                if not body.get("ok"):
                    raise TelegramError(f"Telegram meldet einen Fehler: {body}")
                return int(body["result"]["message_id"])
            if response.status_code < 500:
                raise TelegramError(
                    f"Telegram {response.status_code}: {response.text}"
                )
            last_error = TelegramError(
                f"Telegram {response.status_code}: {response.text}"
            )
            log.warning("Telegram-Versuch %d: %s", attempt, last_error)

        if attempt < RETRIES:
            time.sleep(2**attempt)

    raise TelegramError(f"Senden nach {RETRIES} Versuchen fehlgeschlagen: {last_error}")
