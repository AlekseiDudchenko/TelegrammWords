"""State: which words have been used, and when we last posted."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from random import Random

from .wordlist import Entry

# We post twice a day, so the double-post guard counts half-days ("slots")
# rather than days. Noon UTC splits them; both cron runs sit hours away from
# that line, so the usual Actions delay cannot push a run into the next slot.
SLOT_BOUNDARY_HOUR = 12


def slot_of(moment: datetime) -> str:
    """Name the half-day a run belongs to, e.g. '2026-08-02/am'.

    The names sort chronologically as plain strings — 'am' < 'pm' — which is
    what `already_posted` relies on.
    """
    moment = moment.astimezone(timezone.utc)
    half = "am" if moment.hour < SLOT_BOUNDARY_HOUR else "pm"
    return f"{moment.date().isoformat()}/{half}"


def _slot_from(raw: dict) -> str | None:
    """Read the slot, upgrading state left by the one-post-a-day version.

    That version recorded a bare date and could have posted at any hour, so it
    maps to the *second* slot of the day: the conservative direction, blocking
    the rest of that day rather than risking a duplicate.
    """
    slot = raw.get("last_post_slot")
    if slot:
        return str(slot)
    day = raw.get("last_post_date")
    return f"{day}/pm" if day else None


@dataclass
class State:
    last_post_slot: str | None = None
    cycle: int = 0
    posted: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            last_post_slot=_slot_from(raw),
            cycle=int(raw.get("cycle", 0)),
            posted=list(raw.get("posted", [])),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_post_slot": self.last_post_slot,
            "cycle": self.cycle,
            "posted": self.posted,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def already_posted(self, slot: str) -> bool:
        """True once this slot — or a later one — has been served.

        The comparison is '<=' rather than '==' so that a job re-run from the
        Actions UI, which replays an older slot, stays silent too.
        """
        return self.last_post_slot is not None and slot <= self.last_post_slot

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

    def record(self, word: str, slot: str) -> None:
        if word not in self.posted:
            self.posted.append(word)
        self.last_post_slot = slot
