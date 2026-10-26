"""CLI: post the next collocation, or an explicitly requested word."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from . import audio, cards, collocations, formatter, generator, links, telegram, wordlist
from .config import Config, ConfigError
from .models import WordCard
from .state import State, day_of
from .wordlist import Entry

log = logging.getLogger("bot")

VOICE_CAPTION = "🔊 <i>Beispiele zum Anhören</i>"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bot.main",
        description="Post the next daily collocation to the Telegram channel.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and print the card; send nothing and save nothing.",
    )
    parser.add_argument(
        "--word",
        metavar="WORD",
        help="Post a word card manually instead of the next collocation.",
    )
    parser.add_argument(
        "--level",
        default="B1",
        help="Level for --word when the word is not in the list (default: B1).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Post even if this day has already been served.",
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
        collocation_store = collocations.load(config.collocations_file)
        state = State.load(config.state_file)
        day = day_of(datetime.now(timezone.utc))

        if state.already_posted(day) and not (args.force or args.dry_run):
            log.info("Already posted for day %s — nothing to do.", day)
            return 0

        if not args.word or args.word.casefold() in {
            phrase.casefold() for phrase in collocation_store
        }:
            posted_key, card = collocations.next_card(
                collocation_store, entries, state.posted, requested=args.word
            )
            log.info("Collocation: %s (%s)", card.ausdruck, card.niveau)
            message = formatter.render_collocation(card)
            recording = audio.find(config.audio_dir, card.beispiele)
            if recording is None:
                log.warning("No recording for %r — run python -m bot.audio.", card.ausdruck)
        else:
            stored = cards.load(config.cards_file)
            entry = _pick_entry(args, entries, state, stored)
            log.info("Word: %s (%s)", entry.word, entry.level)
            card = _card_for(entry, stored, config)
            message = formatter.render(card, drillcards=links.resolve_drillcards(card))
            posted_key = entry.word
            recording = None

        if args.dry_run:
            print(message)
            if recording is not None:
                print(f"\n[voice reply: {recording}]")
            return 0

        token, chat_id = config.require_telegram()
        message_id = telegram.send_message(token, chat_id, message)
        log.info("Sent to %s (message_id=%s).", chat_id, message_id)
        if recording is not None:
            _send_recording(token, chat_id, recording, message_id)

        state.record(posted_key, day)
        state.save(config.state_file)
        return 0

    except (ConfigError, wordlist.WordlistError, cards.CardStoreError, collocations.CollocationError) as exc:
        log.error("%s", exc)
        return 2
    except (generator.GenerationError, telegram.TelegramError) as exc:
        log.error("%s", exc)
        return 1


def _send_recording(token: str, chat_id: str, recording: Path, reply_to: int) -> None:
    """Reply to the post with the spoken examples.

    The post is already out, so a failure here must not fail the run: the
    state would stay unsaved and the next run would post the card again.
    """
    try:
        voice_id = telegram.send_voice(
            token, chat_id, recording, reply_to=reply_to, caption=VOICE_CAPTION
        )
    except (telegram.TelegramError, OSError) as exc:
        log.warning("Post sent, but the voice reply failed: %s", exc)
    else:
        log.info("Voice reply sent (message_id=%s).", voice_id)


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
