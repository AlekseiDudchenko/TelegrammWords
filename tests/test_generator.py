"""Der Generator wird gegen einen Fake-Client getestet — keine echten API-Aufrufe."""

import json
from types import SimpleNamespace

import pytest

from bot import generator
from bot.wordlist import Entry

ENTRY = Entry(wort="Haus", niveau="A2")

VALID = {
    "wort": "Haus",
    "artikel": "das",
    "plural": "die Häuser",
    "stammformen": None,
    "wortart": "Substantiv",
    "ipa": "haʊ̯s",
    "niveau": "A2",
    "bedeutungen": ["Gebäude, in dem Menschen wohnen."],
    "etymologie": "Von mittelhochdeutsch hūs.",
    "beispiele": ["Das Haus ist alt."],
    "synonyme": ["Gebäude"],
    "antonyme": [],
    "kollokationen": ["nach Hause gehen"],
}


class FakeClient:
    """Liefert die vorgegebenen Antworten der Reihe nach."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        return self._responses.pop(0)


def reply(text, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
    )


def test_valid_response_is_parsed():
    client = FakeClient(reply(json.dumps(VALID)))
    card = generator.generate(client, "claude-opus-5", ENTRY)
    assert card.wort == "Haus"
    assert card.antonyme == []
    assert client.calls == 1


def test_invalid_response_is_retried_once():
    client = FakeClient(reply("{nicht json"), reply(json.dumps(VALID)))
    card = generator.generate(client, "claude-opus-5", ENTRY)
    assert card.wort == "Haus"
    assert client.calls == 2


def test_two_invalid_responses_fail_loudly():
    missing_field = {k: v for k, v in VALID.items() if k != "etymologie"}
    client = FakeClient(reply("{nicht json"), reply(json.dumps(missing_field)))
    with pytest.raises(generator.GenerationError, match="zwei Versuchen"):
        generator.generate(client, "claude-opus-5", ENTRY)


def test_refusal_is_not_retried():
    client = FakeClient(reply("", stop_reason="refusal"))
    with pytest.raises(generator.GenerationError, match="abgelehnt"):
        generator.generate(client, "claude-opus-5", ENTRY)
    assert client.calls == 1


def test_truncated_response_fails_instead_of_posting_half_a_card():
    client = FakeClient(reply('{"wort": "Ha', stop_reason="max_tokens"))
    with pytest.raises(generator.GenerationError, match="abgeschnitten"):
        generator.generate(client, "claude-opus-5", ENTRY)
