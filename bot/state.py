"""State: which words have been used, and when we last posted."""

from __future__ import annotations

import json
from collections.abc import Sequence
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

    def next_word(
        self, entries: list[Entry], preferred: Sequence[str] = ()
    ) -> Entry:
        """Return the next unused word of the current cycle.

        `preferred` (the words with a stored card) goes first, in the order it
        was given, so no API key is needed until the store is used up. The rest
        follows a shuffle that is deterministic per cycle: it can be reproduced
        from `cycle` alone, and words added to the list mid-rotation don't
        disturb the current round.
        """
        if not entries:
            raise ValueError("word list is empty.")

        done = set(self.posted)
        for _ in range(2):
            for entry in self._ordered(entries, preferred):
                if entry.word not in done:
                    return entry
            # Round complete: new cycle, new order.
            self.cycle += 1
            self.posted = []
            done = set()

        raise AssertionError("unreachable: after a cycle reset every word is free")

    def _ordered(self, entries: list[Entry], preferred: Sequence[str]) -> list[Entry]:
        by_word = {entry.word: entry for entry in entries}
        head = [by_word[word] for word in preferred if word in by_word]
        chosen = {entry.word for entry in head}
        return head + [e for e in self._shuffled(entries) if e.word not in chosen]

    def _shuffled(self, entries: list[Entry]) -> list[Entry]:
        ordered = sorted(entries, key=lambda e: e.word)
        Random(self.cycle).shuffle(ordered)
        return ordered

    def record(self, word: str, today: date) -> None:
        if word not in self.posted:
            self.posted.append(word)
        self.last_post_date = today.isoformat()
