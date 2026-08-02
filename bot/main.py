"""CLI: eine Wortkarte erzeugen und in den Kanal posten."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timezone, datetime

import anthropic

from . import formatter, generator, telegram, wordlist
from .config import Config, ConfigError
from .state import State
from .wordlist import Entry

log = logging.getLogger("bot")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bot.main",
        description="Postet die Wortkarte des Tages in den Telegram-Kanal.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Karte erzeugen und ausgeben, nichts senden und nichts speichern.",
    )
    parser.add_argument(
        "--word",
        metavar="WORT",
        help="Dieses Wort statt des nächsten aus der Liste nehmen.",
    )
    parser.add_argument(
        "--niveau",
        default="B1",
        help="Niveau für --word, wenn das Wort nicht in der Liste steht (Standard: B1).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Auch dann posten, wenn heute schon gepostet wurde.",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug-Logs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        config = Config.from_env()
        entries = wordlist.load(config.words_file)
        state = State.load(config.state_file)
        today = datetime.now(timezone.utc).date()

        if state.already_posted_today(today) and not (args.force or args.dry_run):
            log.info("Für %s wurde bereits gepostet — nichts zu tun.", today)
            return 0

        entry = _pick_entry(args, entries, state)
        log.info("Wort: %s (%s)", entry.wort, entry.niveau)

        client = anthropic.Anthropic(api_key=config.require_anthropic())
        card = generator.generate(client, config.model, entry)
        message = formatter.render(card)

        if args.dry_run:
            print(message)
            return 0

        token, chat_id = config.require_telegram()
        message_id = telegram.send_message(token, chat_id, message)
        log.info("Gesendet an %s (message_id=%s).", chat_id, message_id)

        state.record(entry.wort, today)
        state.save(config.state_file)
        return 0

    except (ConfigError, wordlist.WordlistError) as exc:
        log.error("%s", exc)
        return 2
    except (generator.GenerationError, telegram.TelegramError) as exc:
        log.error("%s", exc)
        return 1


def _pick_entry(args: argparse.Namespace, entries: list[Entry], state: State) -> Entry:
    if not args.word:
        return state.next_word(entries)
    for entry in entries:
        if entry.wort.lower() == args.word.lower():
            return entry
    return Entry(wort=args.word, niveau=args.niveau)


if __name__ == "__main__":
    sys.exit(main())
