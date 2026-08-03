from datetime import datetime, timedelta, timezone

import pytest

from bot.state import State, slot_of
from bot.wordlist import Entry

ENTRIES = [Entry(word=w, level="B1") for w in ("alpha", "beta", "gamma")]


def test_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = State(last_post_slot="2026-08-01/pm", cycle=2, posted=["alpha"])
    state.save(path)

    loaded = State.load(path)
    assert (loaded.last_post_slot, loaded.cycle, loaded.posted) == (
        "2026-08-01/pm",
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
        state.record(entry.word, "2026-08-02/am")
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


def test_the_same_slot_is_served_once():
    state = State(last_post_slot="2026-08-02/am")
    assert state.already_posted("2026-08-02/am")
    assert not state.already_posted("2026-08-02/pm")


def test_both_slots_of_a_day_are_free():
    state = State()
    state.record("alpha", "2026-08-02/am")
    assert not state.already_posted("2026-08-02/pm")

    state.record("beta", "2026-08-02/pm")
    assert state.already_posted("2026-08-02/pm")
    assert not state.already_posted("2026-08-03/am")


def test_a_replayed_older_slot_stays_silent():
    # Re-running yesterday's job from the Actions UI must not post again.
    state = State(last_post_slot="2026-08-02/pm")
    assert state.already_posted("2026-08-02/am")
    assert state.already_posted("2026-08-01/pm")


def test_state_without_a_slot_never_blocks():
    assert not State().already_posted("2026-08-02/am")


def test_slots_split_the_day_at_noon_utc():
    day = datetime(2026, 8, 2, tzinfo=timezone.utc)
    assert slot_of(day.replace(hour=6)) == "2026-08-02/am"
    assert slot_of(day.replace(hour=11, minute=59)) == "2026-08-02/am"
    assert slot_of(day.replace(hour=12)) == "2026-08-02/pm"
    assert slot_of(day.replace(hour=16)) == "2026-08-02/pm"


def test_slots_are_computed_in_utc():
    # 01:00 in Berlin (+02:00) is still the previous evening in UTC.
    berlin = timezone(timedelta(hours=2))
    assert slot_of(datetime(2026, 8, 3, 1, tzinfo=berlin)) == "2026-08-02/pm"


def test_slot_names_sort_chronologically():
    moments = [
        datetime(2026, 8, 2, 6, tzinfo=timezone.utc),
        datetime(2026, 8, 2, 16, tzinfo=timezone.utc),
        datetime(2026, 8, 3, 6, tzinfo=timezone.utc),
    ]
    names = [slot_of(m) for m in moments]
    assert names == sorted(names)


def test_state_from_the_one_post_a_day_version_is_upgraded(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        '{"last_post_date": "2026-08-02", "cycle": 1, "posted": ["alpha"]}',
        encoding="utf-8",
    )
    state = State.load(path)

    # The old version posted at an unknown hour, so the whole day is blocked.
    assert state.already_posted("2026-08-02/am")
    assert state.already_posted("2026-08-02/pm")
    assert not state.already_posted("2026-08-03/am")
    assert (state.cycle, state.posted) == (1, ["alpha"])


def test_empty_wordlist_is_an_error():
    with pytest.raises(ValueError):
        State().next_word([])


def test_preferred_words_come_first_in_their_own_order():
    state = State()
    assert state.next_word(ENTRIES, preferred=["gamma", "alpha"]).word == "gamma"

    state.record("gamma", "2026-08-02/am")
    assert state.next_word(ENTRIES, preferred=["gamma", "alpha"]).word == "alpha"


def test_shuffle_takes_over_once_preferred_words_are_used():
    state = State(posted=["gamma", "alpha"])
    assert state.next_word(ENTRIES, preferred=["gamma", "alpha"]).word == "beta"


def test_unknown_preferred_words_are_ignored():
    state = State()
    assert state.next_word(ENTRIES, preferred=["not-in-the-list"]) in ENTRIES
