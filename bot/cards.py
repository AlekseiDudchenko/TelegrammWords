"""Pre-written cards stored in the repository (data/cards.yml).

The store is what lets the bot run without an API key: a word found here is
posted straight from the file. The Claude API is only used for words that have
no stored card.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import WordCard


class CardStoreError(RuntimeError):
    pass


def load(path: Path) -> dict[str, WordCard]:
    """Read all stored cards, keeping the order of the file.

    A missing file is not an error — it simply means every card comes from the
    API. A malformed one is: a broken card would otherwise surface as a broken
    post months later.
    """
    if not path.exists():
        return {}

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise CardStoreError(f"{path}: expected a mapping of word -> card.")

    cards: dict[str, WordCard] = {}
    for word, payload in raw.items():
        if not isinstance(payload, dict):
            raise CardStoreError(f"{path}: card '{word}' is not a mapping.")
        try:
            card = WordCard.model_validate(payload)
        except ValidationError as exc:
            raise CardStoreError(f"{path}: card '{word}' is invalid: {exc}") from exc
        if card.wort != word:
            raise CardStoreError(
                f"{path}: card '{word}' has a different 'wort' field: '{card.wort}'."
            )
        cards[str(word)] = card

    return cards
