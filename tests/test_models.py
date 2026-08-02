from bot.models import card_json_schema


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
