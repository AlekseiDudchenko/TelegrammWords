"""Laden der Wortliste aus data/words.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Entry:
    wort: str
    niveau: str


class WordlistError(RuntimeError):
    pass


def load(path: Path) -> list[Entry]:
    """Liest die nach Niveau gruppierte Wortliste in eine flache Liste."""
    if not path.exists():
        raise WordlistError(f"Wortliste nicht gefunden: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise WordlistError(
            f"{path}: erwartet wird eine Zuordnung Niveau -> Liste von Wörtern."
        )

    entries: list[Entry] = []
    seen: set[str] = set()
    for niveau, words in raw.items():
        if not isinstance(words, list):
            raise WordlistError(f"{path}: '{niveau}' ist keine Liste.")
        for word in words:
            if not isinstance(word, str) or not word.strip():
                raise WordlistError(f"{path}: ungültiger Eintrag unter '{niveau}': {word!r}")
            word = word.strip()
            if word in seen:
                raise WordlistError(f"{path}: doppelter Eintrag {word!r}")
            seen.add(word)
            entries.append(Entry(wort=word, niveau=str(niveau)))

    if not entries:
        raise WordlistError(f"{path}: Wortliste ist leer.")
    return entries
