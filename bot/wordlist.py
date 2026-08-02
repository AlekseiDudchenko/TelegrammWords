"""Loading the word list from data/words.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Entry:
    word: str
    level: str


class WordlistError(RuntimeError):
    pass


def load(path: Path) -> list[Entry]:
    """Read the level-grouped word list into a flat list."""
    if not path.exists():
        raise WordlistError(f"word list not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise WordlistError(f"{path}: expected a mapping of level -> list of words.")

    entries: list[Entry] = []
    seen: set[str] = set()
    for level, words in raw.items():
        if not isinstance(words, list):
            raise WordlistError(f"{path}: '{level}' is not a list.")
        for word in words:
            if not isinstance(word, str) or not word.strip():
                raise WordlistError(f"{path}: invalid entry under '{level}': {word!r}")
            word = word.strip()
            if word in seen:
                raise WordlistError(f"{path}: duplicate entry {word!r}")
            seen.add(word)
            entries.append(Entry(word=word, level=str(level)))

    if not entries:
        raise WordlistError(f"{path}: word list is empty.")
    return entries
