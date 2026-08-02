"""Zustand: welches Wort war schon dran, und wann wurde zuletzt gepostet."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from random import Random

from .wordlist import Entry


@dataclass
class State:
    last_post_date: str | None = None
    cycle: int = 0
    posted: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            last_post_date=raw.get("last_post_date"),
            cycle=int(raw.get("cycle", 0)),
            posted=list(raw.get("posted", [])),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_post_date": self.last_post_date,
            "cycle": self.cycle,
            "posted": self.posted,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def already_posted_today(self, today: date) -> bool:
        return self.last_post_date == today.isoformat()

    def next_word(self, entries: list[Entry]) -> Entry:
        """Nächstes noch nicht benutztes Wort des aktuellen Zyklus.

        Die Reihenfolge wird pro Zyklus deterministisch gemischt, damit sie sich
        aus `cycle` reproduzieren lässt und neue Wörter in der Liste keine
        laufende Runde durcheinanderbringen.
        """
        if not entries:
            raise ValueError("Wortliste ist leer.")

        done = set(self.posted)
        for _ in range(2):
            for entry in self._shuffled(entries):
                if entry.wort not in done:
                    return entry
            # Runde durch: neuer Zyklus, neue Reihenfolge.
            self.cycle += 1
            self.posted = []
            done = set()

        raise AssertionError("unerreichbar: nach einem Zyklus-Reset ist alles frei")

    def _shuffled(self, entries: list[Entry]) -> list[Entry]:
        ordered = sorted(entries, key=lambda e: e.wort)
        Random(self.cycle).shuffle(ordered)
        return ordered

    def record(self, wort: str, today: date) -> None:
        if wort not in self.posted:
            self.posted.append(wort)
        self.last_post_date = today.isoformat()
