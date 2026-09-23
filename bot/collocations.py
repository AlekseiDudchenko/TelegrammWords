"""Reviewed collocation cards for the daily channel post."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from .wordlist import Entry


class CollocationError(RuntimeError):
    pass


class CollocationCard(BaseModel):
    ausdruck: str = Field(min_length=1)
    niveau: str
    bedeutung: str = Field(min_length=1)
    beispiele: list[str] = Field(min_length=2, max_length=3)
    beispiele_en: list[str] = Field(min_length=2, max_length=3)
    gebrauch: str = Field(min_length=1)

    @model_validator(mode="after")
    def translations_match(self) -> "CollocationCard":
        if len(self.beispiele) != len(self.beispiele_en):
            raise ValueError("Each example needs an English translation.")
        return self


def load(path: Path) -> dict[str, CollocationCard]:
    if not path.exists():
        raise CollocationError(f"Collocation file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise CollocationError(f"{path}: expected a nonempty mapping of phrase to card.")
    result: dict[str, CollocationCard] = {}
    for phrase, payload in raw.items():
        try:
            card = CollocationCard.model_validate(payload)
        except ValidationError as exc:
            raise CollocationError(f"{path}: invalid card {phrase!r}: {exc}") from exc
        if card.ausdruck != phrase:
            raise CollocationError(f"{path}: key and ausdruck differ: {phrase!r}.")
        result[phrase] = card
    return result


def next_card(
    store: dict[str, CollocationCard],
    entries: list[Entry],
    posted: list[str],
    requested: str | None = None,
) -> tuple[str, CollocationCard]:
    """Select a listed phrase in card order, preserving the mixed-level rotation."""
    levels = {entry.word: entry.level for entry in entries}
    for phrase, card in store.items():
        if levels.get(phrase) != card.niveau:
            raise CollocationError(
                f"{phrase!r} must appear in words.yml at level {card.niveau}."
            )

    if requested is not None:
        for phrase, card in store.items():
            if phrase.casefold() == requested.casefold():
                return f"collocation:{phrase}", card
        raise CollocationError(f"No stored collocation: {requested!r}.")

    for phrase, card in store.items():
        key = f"collocation:{phrase}"
        if key not in posted:
            return key, card
    raise CollocationError("All stored collocations have been posted. Add more cards before the next run.")
