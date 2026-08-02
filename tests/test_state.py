from datetime import date

import pytest

from bot.state import State
from bot.wordlist import Entry

ENTRIES = [Entry(word=w, level="B1") for w in ("alpha", "beta", "gamma")]


def test_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = State(last_post_date="2026-08-01", cycle=2, posted=["alpha"])
    state.save(path)

    loaded = State.load(path)
    assert (loaded.last_post_date, loaded.cycle, loaded.posted) == (
        "2026-08-01",
        2,
        ["alpha"],
    )


def test_missing_file_gives_empty_state(tmp_path):
    state = State.load(tmp_path / "nothing.json")
    assert state.posted == [] and state.cycle == 0


def test_no_repeats_within_a_cycle():
    state = State()
    seen = []
    for _ in range(len(ENTRIES)):
        entry = state.next_word(ENTRIES)
        seen.append(entry.word)
        state.record(entry.word, date(2026, 8, 2))
    assert sorted(seen) == ["alpha", "beta", "gamma"]
    assert state.cycle == 0


def test_exhausted_list_starts_a_new_cycle():
    state = State(cycle=0, posted=[e.word for e in ENTRIES])
    entry = state.next_word(ENTRIES)
    assert state.cycle == 1
    assert state.posted == []
    assert entry in ENTRIES


def test_order_is_deterministic_per_cycle():
    assert State(cycle=7).next_word(ENTRIES) == State(cycle=7).next_word(ENTRIES)


def test_already_posted_today():
    state = State(last_post_date="2026-08-02")
    assert state.already_posted_today(date(2026, 8, 2))
    assert not state.already_posted_today(date(2026, 8, 3))


def test_empty_wordlist_is_an_error():
    with pytest.raises(ValueError):
        State().next_word([])


def test_preferred_words_come_first_in_their_own_order():
    state = State()
    assert state.next_word(ENTRIES, preferred=["gamma", "alpha"]).word == "gamma"

    state.record("gamma", date(2026, 8, 2))
    assert state.next_word(ENTRIES, preferred=["gamma", "alpha"]).word == "alpha"


def test_shuffle_takes_over_once_preferred_words_are_used():
    state = State(posted=["gamma", "alpha"])
    assert state.next_word(ENTRIES, preferred=["gamma", "alpha"]).word == "beta"


def test_unknown_preferred_words_are_ignored():
    state = State()
    assert state.next_word(ENTRIES, preferred=["not-in-the-list"]) in ENTRIES
