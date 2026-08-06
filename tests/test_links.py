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


def test_drillcards_url_uses_level_and_word_in_lowercase():
    url = links.drillcards_url(
        card(wort="widersprechen", wortart="Verb", niveau="B2", artikel=None)
    )
    assert url == "https://drillcards.org/de/words/b2/widersprechen"


def test_drillcards_url_lowercases_a_noun():
    assert links.drillcards_url(card()) == "https://drillcards.org/de/words/a2/haus"


def test_drillcards_url_encodes_umlauts():
    assert links.drillcards_url(card(wort="Grüße")).endswith("/gr%C3%BC%C3%9Fe")


class FakeResponse:
    """Just the three attributes `resolve_drillcards` reads off a response."""

    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = httpx.URL(url)


def answer(monkeypatch, status_code: int, final_url: str | None = None, calls=None):
    """Make every HEAD/GET return one canned response, recording the method."""

    def respond(method: str):
        def handler(url, **kwargs):
            if calls is not None:
                calls.append(method)
            return FakeResponse(status_code, final_url or str(url))

        return handler

    monkeypatch.setattr(links.httpx, "head", respond("head"))
    monkeypatch.setattr(links.httpx, "get", respond("get"))


def test_drillcards_link_is_kept_when_the_page_answers_200(monkeypatch):
    answer(monkeypatch, 200)
    assert links.resolve_drillcards(card()) == "https://drillcards.org/de/words/a2/haus"


@pytest.mark.parametrize("status_code", [404, 403, 410, 500, 503])
def test_drillcards_link_is_dropped_when_the_page_is_not_200(monkeypatch, status_code):
    answer(monkeypatch, status_code)
    assert links.resolve_drillcards(card()) is None


def test_drillcards_link_is_dropped_when_the_request_fails(monkeypatch):
    def explode(url, **kwargs):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(links.httpx, "head", explode)
    monkeypatch.setattr(links.httpx, "get", explode)
    assert links.resolve_drillcards(card()) is None


def test_drillcards_link_is_dropped_when_redirected_to_another_page(monkeypatch):
    answer(monkeypatch, 200, final_url="https://drillcards.org/de/words")
    assert links.resolve_drillcards(card()) is None


def test_a_redirect_that_stays_on_the_word_still_counts(monkeypatch):
    answer(monkeypatch, 200, final_url="https://drillcards.org/de/words/a2/haus/")
    assert links.resolve_drillcards(card()) is not None


def test_a_percent_encoded_umlaut_in_the_final_url_still_counts(monkeypatch):
    answer(monkeypatch, 200, final_url="https://drillcards.org/de/words/a2/%C3%BCben")
    assert links.resolve_drillcards(card(wort="üben", wortart="Verb")) is not None


def test_head_is_tried_first_and_get_only_when_head_is_refused(monkeypatch):
    calls: list[str] = []
    answer(monkeypatch, 200, calls=calls)
    links.resolve_drillcards(card())
    assert calls == ["head"]

    calls.clear()
    answer(monkeypatch, 405, calls=calls)
    links.resolve_drillcards(card())
    assert calls == ["head", "get"]


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
