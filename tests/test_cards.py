import pytest
import yaml

from bot import cards, formatter, wordlist
from bot.config import DEFAULT_DATA_DIR

STORE = DEFAULT_DATA_DIR / "cards.yml"

MINIMAL = {
    "wort": "Haus",
    "artikel": "das",
    "plural": "die Häuser",
    "stammformen": None,
    "wortart": "Substantiv",
    "ipa": "haʊ̯s",
    "niveau": "A2",
    "bedeutungen": ["Ein Gebäude, in dem Menschen wohnen."],
    "beispiele": ["Das Haus steht leer."],
    "beispiele_en": ["The house stands empty."],
    "synonyme": ["Gebäude"],
    "antonyme": [],
    "kollokationen": ["nach Hause gehen"],
}


def write(tmp_path, payload):
    path = tmp_path / "cards.yml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def test_repo_store_is_valid_and_covers_a_month():
    # Two posts a day, so a month of cover needs sixty cards.
    stored = cards.load(STORE)
    assert len(stored) >= 60


def test_every_stored_word_is_in_the_wordlist():
    entries = {e.word: e for e in wordlist.load(DEFAULT_DATA_DIR / "words.yml")}
    stored = cards.load(STORE)

    missing = sorted(set(stored) - set(entries))
    assert not missing, f"cards for words that are not in words.yml: {missing}"

    mismatched = sorted(w for w, c in stored.items() if c.niveau != entries[w].level)
    assert not mismatched, f"card level differs from words.yml: {mismatched}"


def test_every_stored_card_renders():
    for word, card in cards.load(STORE).items():
        message = formatter.render(card)
        assert word in message
        # Telegram rejects messages over 4096 characters.
        assert len(message) < 4096, word


def test_every_stored_example_has_a_translation():
    for word, card in cards.load(STORE).items():
        # The schema already pairs the lists; this catches an empty one.
        assert card.beispiele_en, f"{word}: no English translations"
        assert all(s.strip() for s in card.beispiele_en), f"{word}: empty translation"


def test_missing_file_is_an_empty_store(tmp_path):
    assert cards.load(tmp_path / "nothing.yml") == {}


def test_card_is_validated(tmp_path):
    broken = dict(MINIMAL)
    del broken["ipa"]
    with pytest.raises(cards.CardStoreError):
        cards.load(write(tmp_path, {"Haus": broken}))


def test_key_must_match_the_headword(tmp_path):
    with pytest.raises(cards.CardStoreError):
        cards.load(write(tmp_path, {"Hütte": MINIMAL}))


def test_file_order_is_kept(tmp_path):
    path = tmp_path / "cards.yml"
    second = dict(MINIMAL, wort="Traum", artikel="der", plural="die Träume")
    path.write_text(
        yaml.safe_dump({"Traum": second}, allow_unicode=True, sort_keys=False)
        + yaml.safe_dump({"Haus": MINIMAL}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    assert list(cards.load(path)) == ["Traum", "Haus"]
