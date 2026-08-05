import pytest
from pydantic import ValidationError

from bot.models import WordCard, card_json_schema


def test_schema_is_strict_everywhere():
    schema = card_json_schema()
    _assert_strict(schema)


def test_all_fields_are_required():
    schema = card_json_schema()
    assert set(schema["required"]) == set(schema["properties"])
    assert "antonyme" in schema["required"]


def test_optional_fields_accept_null():
    artikel = card_json_schema()["properties"]["artikel"]
    types = {variant.get("type") for variant in artikel["anyOf"]}
    assert types == {"string", "null"}


def _assert_strict(node):
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            assert node["additionalProperties"] is False
        for value in node.values():
            _assert_strict(value)
    elif isinstance(node, list):
        for item in node:
            _assert_strict(item)


def test_translations_must_match_the_examples_one_to_one():
    payload = dict(
        wort="Haus",
        artikel="das",
        plural="die Häuser",
        stammformen=None,
        wortart="Substantiv",
        ipa="haʊ̯s",
        niveau="A2",
        bedeutungen=["Gebäude, in dem Menschen wohnen."],
        beispiele=["Das Haus ist alt.", "Das Haus steht leer."],
        beispiele_en=["The house is old."],
        synonyme=["Gebäude"],
        antonyme=[],
        kollokationen=["nach Hause gehen"],
    )
    with pytest.raises(ValidationError, match="beispiele_en"):
        WordCard.model_validate(payload)

    payload["beispiele_en"] = ["The house is old.", "The house stands empty."]
    assert len(WordCard.model_validate(payload).beispiele_en) == 2
