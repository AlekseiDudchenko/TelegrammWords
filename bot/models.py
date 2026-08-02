"""The word card schema, which doubles as the JSON schema for Claude's reply.

Field names stay German because they mirror German grammatical categories and
are part of the data the bot renders. Everything the model writes into them is
German too — the field descriptions below say so explicitly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


class WordCard(BaseModel):
    """A monolingual German word card. All values are written in German."""

    wort: str = Field(description="The headword in its base form, without article.")
    artikel: str | None = Field(
        description="der/die/das for nouns, null otherwise.",
    )
    plural: str | None = Field(
        description="Plural form for nouns (e.g. 'die Häuser'), null otherwise.",
    )
    stammformen: str | None = Field(
        description=(
            "For verbs, the principal parts, e.g. 'gehen – ging – ist gegangen'. "
            "Null otherwise."
        ),
    )
    wortart: str = Field(
        description=(
            "Part of speech, named in German: Substantiv, Verb, Adjektiv, "
            "Adverb, Präposition, Konjunktion …"
        ),
    )
    ipa: str = Field(description="IPA transcription, without square brackets.")
    niveau: str = Field(description=f"CEFR level, one of: {', '.join(LEVELS)}.")
    bedeutungen: list[str] = Field(
        description=(
            "1 to 3 meanings, each explained in German in one short sentence, "
            "monolingual and without numbering."
        ),
    )
    etymologie: str = Field(
        description=(
            "Origin of the word in German, 2 to 4 sentences: Old High German, "
            "Middle High German, Latin or Greek roots, and shifts in meaning. "
            "Do not invent anything — if the origin is disputed or unclear, say "
            "so explicitly."
        ),
    )
    beispiele: list[str] = Field(
        description="2 to 3 complete German example sentences containing the headword.",
    )
    synonyme: list[str] = Field(
        description="3 to 5 German synonyms — single words or short phrases only.",
    )
    antonyme: list[str] = Field(
        description=(
            "0 to 4 German antonyms. Return an empty list when the word has no "
            "genuine opposite — do not invent one."
        ),
    )
    kollokationen: list[str] = Field(
        description="2 to 3 German set phrases or typical collocations.",
    )


def card_json_schema() -> dict[str, Any]:
    """Prepare the pydantic schema for structured outputs.

    The API requires `additionalProperties: false` and every field listed in
    `required`. Optional fields are covered by `str | None`: the model must
    return them but may set null.
    """
    schema = WordCard.model_json_schema()
    _tighten(schema)
    return schema


def _tighten(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"])
        # Titles only bloat the schema.
        node.pop("title", None)
        for value in node.values():
            _tighten(value)
    elif isinstance(node, list):
        for item in node:
            _tighten(item)
