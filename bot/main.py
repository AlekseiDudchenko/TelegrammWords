"""CLI: generate one word card and post it to the channel."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

import anthropic

from . import cards, formatter, generator, telegram, wordlist
from .config import Config, ConfigError
from .models import WordCard
from .state import State
from .wordlist import Entry

log = logging.getLogger("bot")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bot.main",
        description="Post the word card of the day to the Telegram channel.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and print the card; send nothing and save nothing.",
    )
    parser.add_argument(
        "--word",
        metavar="WORD",
        help="Use this word instead of the next one from the list.",
    )
    parser.add_argument(
        "--level",
        default="B1",
        help="Level for --word when the word is not in the list (default: B1).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Post even if something was already posted today.",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging.")
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
        stored = cards.load(config.cards_file)
        state = State.load(config.state_file)
        today = datetime.now(timezone.utc).date()

        if state.already_posted_today(today) and not (args.force or args.dry_run):
            log.info("Already posted for %s — nothing to do.", today)
            return 0

        entry = _pick_entry(args, entries, state, stored)
        log.info("Word: %s (%s)", entry.word, entry.level)

        card = _card_for(entry, stored, config)
        message = formatter.render(card)

        if args.dry_run:
            print(message)
            return 0

        token, chat_id = config.require_telegram()
        message_id = telegram.send_message(token, chat_id, message)
        log.info("Sent to %s (message_id=%s).", chat_id, message_id)

        state.record(entry.word, today)
        state.save(config.state_file)
        return 0

    except (ConfigError, wordlist.WordlistError, cards.CardStoreError) as exc:
        log.error("%s", exc)
        return 2
    except (generator.GenerationError, telegram.TelegramError) as exc:
        log.error("%s", exc)
        return 1


def _pick_entry(
    args: argparse.Namespace,
    entries: list[Entry],
    state: State,
    stored: dict[str, WordCard],
) -> Entry:
    if not args.word:
        return state.next_word(entries, preferred=list(stored))
    for entry in entries:
        if entry.word.lower() == args.word.lower():
            return entry
    return Entry(word=args.word, level=args.level)


def _card_for(entry: Entry, stored: dict[str, WordCard], config: Config) -> WordCard:
    """Prefer the card written by hand; ask Claude only for the rest."""
    card = stored.get(entry.word)
    if card is not None:
        log.info("Using the stored card from %s.", config.cards_file.name)
        return card

    log.info("No stored card — generating one with %s.", config.model)
    client = anthropic.Anthropic(api_key=config.require_anthropic())
    return generator.generate(client, config.model, entry)


if __name__ == "__main__":
    sys.exit(main())
