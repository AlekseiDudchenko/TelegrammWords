import pytest

from bot import collocations, formatter, main, wordlist
from bot.config import DEFAULT_DATA_DIR
from bot.state import State


def test_sixty_stored_collocations_render_without_an_app_link():
    store = collocations.load(DEFAULT_DATA_DIR / "collocations.yml")
    entries = {e.word: e.level for e in wordlist.load(DEFAULT_DATA_DIR / "words.yml")}
    assert len(store) == 60
    for phrase, card in store.items():
        assert phrase == card.ausdruck
        assert entries[phrase] == card.niveau
        out = formatter.render_collocation(card)
        assert phrase in out
        assert out.count("<tg-spoiler>") == 2
        assert "DrillCards" not in out
        assert len(out) < 4096


def test_collocations_are_selected_in_order_without_repeating():
    store = collocations.load(DEFAULT_DATA_DIR / "collocations.yml")
    entries = wordlist.load(DEFAULT_DATA_DIR / "words.yml")
    state = State(posted=["Freizeit"])
    first_key, first_card = collocations.next_card(store, entries, state.posted)
    assert first_card.ausdruck == "eine Entscheidung treffen"
    state.record(first_key, "2026-09-24")
    assert collocations.next_card(store, entries, state.posted)[1].ausdruck == "eine Pause machen"


def test_dry_run_needs_neither_an_api_key_nor_an_app_lookup(monkeypatch, capsys):
    def unexpected(*args, **kwargs):
        raise AssertionError("An API call was attempted")

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(main.State, "load", lambda _: State())
    monkeypatch.setattr(main.anthropic, "Anthropic", unexpected)
    monkeypatch.setattr(main.links, "resolve_drillcards", unexpected)
    assert main.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Kollokation des Tages" in out
    assert "eine Entscheidung treffen" in out
    assert "DrillCards" not in out


def test_app_link_is_only_shown_when_provided():
    card = next(iter(collocations.load(DEFAULT_DATA_DIR / "collocations.yml").values()))
    out = formatter.render_collocation(card, app_url="https://example.org/a?x=1&y=2")
    assert 'href="https://example.org/a?x=1&amp;y=2"' in out


def test_a_listed_collocation_can_be_previewed_with_word_option(monkeypatch, capsys):
    monkeypatch.setattr(main.State, "load", lambda _: State())
    assert main.main(["--dry-run", "--word", "EINE ENTSCHEIDUNG TREFFEN"]) == 0
    assert "<b>eine Entscheidung treffen</b>" in capsys.readouterr().out


def test_collocation_missing_from_wordlist_is_rejected():
    store = collocations.load(DEFAULT_DATA_DIR / "collocations.yml")
    entries = wordlist.load(DEFAULT_DATA_DIR / "words.yml")
    entries = [e for e in entries if e.word != "eine Entscheidung treffen"]
    with pytest.raises(collocations.CollocationError, match="words.yml"):
        collocations.next_card(store, entries, [])


def test_exhausted_collocations_do_not_fall_back_to_words(monkeypatch):
    store = collocations.load(DEFAULT_DATA_DIR / "collocations.yml")
    all_posted = [f"collocation:{phrase}" for phrase in store]
    monkeypatch.setattr(main.State, "load", lambda _: State(posted=all_posted))
    monkeypatch.setattr(main.anthropic, "Anthropic", lambda *a, **k: pytest.fail("API called"))
    assert main.main(["--dry-run"]) == 2
