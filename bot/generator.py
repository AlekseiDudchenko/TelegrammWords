"""Generate a word card through the Claude API (structured outputs)."""

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
You are a lexicographer writing monolingual word cards for learners of German.

Every value you produce is written in German. Never translate into another
language, and never mix languages inside a field.

Rules:
- Keep definitions simple: explain the headword using vocabulary below its own
  level.
- Synonyms and antonyms: only real, current words. Prefer fewer over
  constructed ones. If there is no meaningful antonym, return an empty list.
- Example sentences: natural contemporary German, each containing the headword.
"""


class GenerationError(RuntimeError):
    pass


def generate(client: anthropic.Anthropic, model: str, entry: Entry) -> WordCard:
    """Ask Claude for a word card and validate the reply.

    An invalid result is retried exactly once; after that the run fails rather
    than posting a broken card.
    """
    schema = card_json_schema()
    prompt = (
        f"Write the word card for the German word '{entry.word}'.\n"
        f"Expected level: {entry.level}. If your own judgement differs, put the "
        f"level you consider correct in the 'niveau' field."
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
                f"the request for '{entry.word}' was refused (stop_reason=refusal)."
            )
        if response.stop_reason == "max_tokens":
            raise GenerationError(
                f"the reply for '{entry.word}' was truncated at "
                f"max_tokens={MAX_TOKENS}."
            )

        text = _first_text(response)
        try:
            return WordCard.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            log.warning("attempt %d for '%s' was invalid: %s", attempt, entry.word, exc)

    raise GenerationError(
        f"no valid card for '{entry.word}' after two attempts: {last_error}"
    )


def _first_text(response: anthropic.types.Message) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    raise GenerationError("the reply contains no text block.")
