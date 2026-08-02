import pytest

from bot.config import DEFAULT_DATA_DIR
from bot import wordlist


def test_repo_wordlist_loads():
    entries = wordlist.load(DEFAULT_DATA_DIR / "words.yml")
    assert len(entries) > 100
    assert all(e.niveau in {"A1", "A2", "B1", "B2", "C1", "C2"} for e in entries)


def test_duplicates_are_rejected(tmp_path):
    path = tmp_path / "words.yml"
    path.write_text("B1:\n  - Haus\nB2:\n  - Haus\n", encoding="utf-8")
    with pytest.raises(wordlist.WordlistError, match="doppelter"):
        wordlist.load(path)


def test_missing_file(tmp_path):
    with pytest.raises(wordlist.WordlistError):
        wordlist.load(tmp_path / "nope.yml")


def test_empty_file(tmp_path):
    path = tmp_path / "words.yml"
    path.write_text("", encoding="utf-8")
    with pytest.raises(wordlist.WordlistError, match="leer"):
        wordlist.load(path)
