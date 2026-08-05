import pytest

from bot import links
from bot.models import WordCard

BASE = dict(
    wort="Haus",
    artikel="das",
    plural="die Häuser",
    stammformen=None,
    wortart="Substantiv",
    ipa="haʊ̯s",
    niveau="A2",
    bedeutungen=["Gebäude, in dem Menschen wohnen."],
    beispiele=["Wir wohnen in einem alten Haus."],
    beispiele_en=["We live in an old house."],
    synonyme=["Gebäude"],
    antonyme=[],
    kollokationen=["nach Hause gehen"],
)


def card(**overrides) -> WordCard:
    return WordCard(**{**BASE, **overrides})


def test_context_url_pairs_german_with_english():
    assert links.context_url(card()) == (
        "https://context.reverso.net/translation/german-english/Haus"
    )


def test_context_url_encodes_umlauts():
    assert links.context_url(card(wort="Grüße")).endswith("/Gr%C3%BC%C3%9Fe")


def test_conjugation_url_is_lowercase():
    url = links.conjugation_url(card(wort="Gehen", wortart="Verb"))
    assert url == "https://conjugator.reverso.net/conjugation-german-verb-gehen.html"


def test_no_conjugation_url_for_a_noun():
    assert links.conjugation_url(card()) is None


@pytest.mark.parametrize(
    "wortart",
    ["Verb", "verb", "unregelmäßiges Verb", "Verb (trennbar)", "Modalverb", "Hilfsverb"],
)
def test_word_classes_counted_as_verbs(wortart):
    assert links.is_verb(card(wortart=wortart))


@pytest.mark.parametrize("wortart", ["Adverb", "Substantiv", "Adjektiv", "Präposition"])
def test_word_classes_not_counted_as_verbs(wortart):
    assert not links.is_verb(card(wortart=wortart))
