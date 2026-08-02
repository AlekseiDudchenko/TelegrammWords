"""Wortkarte über die Claude API erzeugen (Structured Outputs)."""

from __future__ import annotations

import json
import logging

import anthropic
from pydantic import ValidationError

from .models import WordCard, card_json_schema
from .wordlist import Entry

log = logging.getLogger(__name__)

MAX_TOKENS = 8000

SYSTEM_PROMPT = """\
Du bist Lexikograf und schreibst einsprachige Wortkarten für Deutschlernende.

Regeln:
- Alles ausschließlich auf Deutsch. Keine Übersetzungen in andere Sprachen.
- Definitionen einfach halten: erkläre das Wort mit Wortschatz, der unter dem \
Niveau des Stichworts liegt.
- Etymologie: nur belegte Herkunft. Wenn die Herkunft umstritten oder unklar \
ist, sage das ausdrücklich, statt eine Erklärung zu erfinden.
- Synonyme und Antonyme: nur echte, gebräuchliche Wörter. Lieber weniger als \
konstruierte. Gibt es keine sinnvollen Antonyme, gib eine leere Liste zurück.
- Beispielsätze: natürliches Gegenwartsdeutsch, jeder Satz enthält das Stichwort.
"""


class GenerationError(RuntimeError):
    pass


def generate(client: anthropic.Anthropic, model: str, entry: Entry) -> WordCard:
    """Fragt Claude nach einer Wortkarte und validiert die Antwort.

    Ein ungültiges Ergebnis wird genau einmal wiederholt; danach schlägt der
    Lauf fehl, statt eine kaputte Karte zu posten.
    """
    schema = card_json_schema()
    prompt = (
        f"Erstelle die Wortkarte für das Wort «{entry.wort}».\n"
        f"Erwartetes Niveau: {entry.niveau}. Weicht dein eigenes Urteil davon ab, "
        f"trage im Feld 'niveau' das ein, das du für richtig hältst."
    )

    last_error: Exception | None = None
    for attempt in (1, 2):
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": schema},
            },
            messages=[{"role": "user", "content": prompt}],
        )

        if response.stop_reason == "refusal":
            raise GenerationError(
                f"Anfrage für «{entry.wort}» wurde abgelehnt "
                f"(stop_reason=refusal)."
            )
        if response.stop_reason == "max_tokens":
            raise GenerationError(
                f"Antwort für «{entry.wort}» wurde bei max_tokens={MAX_TOKENS} "
                f"abgeschnitten."
            )

        text = _first_text(response)
        try:
            return WordCard.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            log.warning("Versuch %d für «%s» ungültig: %s", attempt, entry.wort, exc)

    raise GenerationError(
        f"Keine gültige Wortkarte für «{entry.wort}» nach zwei Versuchen: {last_error}"
    )


def _first_text(response: anthropic.types.Message) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    raise GenerationError("Antwort enthält keinen Textblock.")
