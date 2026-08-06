"""Tell the maintainer, over Telegram, that a run did not deliver a post.

Alerts go to `TELEGRAM_ALERT_CHAT_ID` — a private chat with the bot, never
the channel. When that variable is unset there is nobody to tell, so an
alert is dropped with a warning in the log rather than raising: alerting is
a diagnostic, and a missing diagnostic must not turn a green run red.
"""

from __future__ import annotations

import argparse
import html
import logging
import os
import sys

from . import telegram
from .config import ALERT_CHAT_VAR, Config

log = logging.getLogger("bot.alert")

PREFIX = "⚠️ <b>Wort des Tages</b>"


def send(config: Config, text: str) -> bool:
    """Send one alert. Returns False when alerting is not configured."""
    if not config.telegram_alert_chat_id:
        log.warning("%s is not set — alert dropped: %s", ALERT_CHAT_VAR, text)
        return False
    if not config.telegram_bot_token:
        log.warning("TELEGRAM_BOT_TOKEN is not set — alert dropped: %s", text)
        return False

    body = f"{PREFIX}\n{html.escape(text)}"
    telegram.send_message(
        config.telegram_bot_token, config.telegram_alert_chat_id, body
    )
    log.info("Alert delivered to %s.", config.telegram_alert_chat_id)
    return True


def run_url() -> str | None:
    """Link to the workflow run we are reporting on, when inside Actions."""
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not (repo and run_id):
        return None
    return f"{server}/{repo}/actions/runs/{run_id}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bot.alert",
        description="Send an operational alert to the maintainer's chat.",
    )
    parser.add_argument("text", help="What went wrong, in a line or two.")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    link = run_url()
    text = f"{args.text}\n{link}" if link else args.text
    try:
        send(Config.from_env(), text)
    except telegram.TelegramError as exc:
        log.error("The alert itself could not be delivered: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
