import httpx
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


INDEX = {"haus": "a1", "widersprechen": "b2", "ueben": "a2", "gruesse": "b1"}


class FakeResponse:
    """Just the parts of a response `_word_index` reads."""

    def __init__(self, status_code=200, payload=None, invalid=False):
        self.status_code = status_code
        self._payload = payload
        self._invalid = invalid

    def json(self):
        if self._invalid:
            raise ValueError("not JSON")
        return self._payload


def serve(monkeypatch, response):
    """Answer the one request `resolve_drillcards` makes with this response."""

    def handler(url, **kwargs):
        assert url == links.DRILLCARDS_INDEX
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(links.httpx, "get", handler)


def serve_index(monkeypatch, index=None):
    serve(monkeypatch, FakeResponse(payload=INDEX if index is None else index))


@pytest.mark.parametrize(
    "word, slug",
    [
        ("Haus", "haus"),
        ("widersprechen", "widersprechen"),
        ("üben", "ueben"),
        ("Grüße", "gruesse"),
        ("Löffel", "loeffel"),
        ("Abhängigkeit", "abhaengigkeit"),
        # The article is not part of the word, and neither is punctuation.
        ("die Straße", "strasse"),
        ("Auto-Fahrt", "auto-fahrt"),
    ],
)
def test_slug_follows_the_sites_own_rules(word, slug):
    """Umlauts are transliterated, not percent-encoded — 'üben' is 'ueben'."""
    assert links.drillcards_slug(card(wort=word)) == slug


def test_drillcards_link_uses_the_deck_from_the_index(monkeypatch):
    serve_index(monkeypatch)
    url = links.resolve_drillcards(card(wort="widersprechen", wortart="Verb"))
    assert url == "https://drillcards.org/de/words/b2/widersprechen"


def test_the_deck_wins_over_the_cards_own_level(monkeypatch):
    """'Haus' is A2 here but sits in the a1 deck — only a1 resolves."""
    serve_index(monkeypatch)
    assert links.resolve_drillcards(card(niveau="A2")) == (
        "https://drillcards.org/de/words/a1/haus"
    )


def test_no_link_for_a_word_drillcards_does_not_have(monkeypatch):
    serve_index(monkeypatch)
    assert links.resolve_drillcards(card(wort="Fernweh")) is None


@pytest.mark.parametrize("status_code", [301, 403, 404, 500, 503])
def test_no_link_when_the_index_does_not_answer_200(monkeypatch, status_code):
    serve(monkeypatch, FakeResponse(status_code=status_code, payload=INDEX))
    assert links.resolve_drillcards(card()) is None


def test_no_link_when_the_index_cannot_be_reached(monkeypatch):
    serve(monkeypatch, httpx.ConnectTimeout("timed out"))
    assert links.resolve_drillcards(card()) is None


def test_no_link_when_the_index_is_not_valid_json(monkeypatch):
    serve(monkeypatch, FakeResponse(invalid=True))
    assert links.resolve_drillcards(card()) is None


@pytest.mark.parametrize(
    "payload", [None, ["haus"], "haus", {"haus": None}, {"haus": ""}, {"haus": 1}]
)
def test_no_link_when_the_index_has_the_wrong_shape(monkeypatch, payload):
    serve(monkeypatch, FakeResponse(payload=payload))
    assert links.resolve_drillcards(card()) is None


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
