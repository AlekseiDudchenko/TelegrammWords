"""Schema der Wortkarte — zugleich das JSON-Schema für die Claude-Antwort."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

NIVEAUS = ("A1", "A2", "B1", "B2", "C1", "C2")


class WordCard(BaseModel):
    """Eine einsprachige Wortkarte. Alle Texte sind auf Deutsch."""

    wort: str = Field(description="Das Stichwort in Grundform, ohne Artikel.")
    artikel: str | None = Field(
        description="der/die/das bei Substantiven, sonst null.",
    )
    plural: str | None = Field(
        description="Pluralform bei Substantiven (z. B. 'die Häuser'), sonst null.",
    )
    stammformen: str | None = Field(
        description=(
            "Bei Verben die Stammformen, z. B. 'gehen – ging – ist gegangen'. "
            "Sonst null."
        ),
    )
    wortart: str = Field(
        description="Substantiv, Verb, Adjektiv, Adverb, Präposition, Konjunktion …",
    )
    ipa: str = Field(description="Lautschrift in IPA, ohne eckige Klammern.")
    niveau: str = Field(description=f"GER-Niveau, eines von: {', '.join(NIVEAUS)}.")
    bedeutungen: list[str] = Field(
        description=(
            "1 bis 3 Bedeutungen, einsprachig auf Deutsch erklärt, je ein kurzer "
            "Satz ohne Nummerierung."
        ),
    )
    etymologie: str = Field(
        description=(
            "Herkunft des Wortes in 2 bis 4 Sätzen: althochdeutsche, "
            "mittelhochdeutsche, lateinische oder griechische Wurzeln, "
            "Bedeutungswandel. Keine erfundenen Angaben — bei unsicherer "
            "Herkunft das ausdrücklich sagen."
        ),
    )
    beispiele: list[str] = Field(
        description="2 bis 3 vollständige Beispielsätze, die das Wort enthalten.",
    )
    synonyme: list[str] = Field(
        description="3 bis 5 Synonyme, nur einzelne Wörter oder kurze Wendungen.",
    )
    antonyme: list[str] = Field(
        description=(
            "0 bis 4 Antonyme. Leere Liste, wenn es keine echten Gegenwörter "
            "gibt — nichts erfinden."
        ),
    )
    kollokationen: list[str] = Field(
        description="2 bis 3 feste Wendungen oder typische Kollokationen.",
    )


def card_json_schema() -> dict[str, Any]:
    """Pydantic-Schema für Structured Outputs aufbereiten.

    Die API verlangt `additionalProperties: false` und dass jedes Feld in
    `required` steht. Optionale Felder sind über `str | None` abgedeckt: das
    Modell muss sie liefern, darf aber null einsetzen.
    """
    schema = WordCard.model_json_schema()
    _tighten(schema)
    return schema


def _tighten(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"])
        # Titles blähen das Schema nur auf.
        node.pop("title", None)
        for value in node.values():
            _tighten(value)
    elif isinstance(node, list):
        for item in node:
            _tighten(item)
