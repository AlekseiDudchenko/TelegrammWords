"""Outbound links for a word card.

Reverso first: the word in Reverso Context, and — for verbs only — its
conjugation table. Reverso Context always needs a language pair, so this is the
one place where the otherwise monolingual card points at a translation;
`CONTEXT_LANGUAGE` decides which one. Then DrillCards, where the same word can
be drilled; that link closes every post.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from .models import WordCard

# The other half of the Reverso Context pair. English matches the language the
# hidden example translations are written in. Any language Reverso supports
# works here: english, russian, french, spanish …
CONTEXT_LANGUAGE = "english"

CONTEXT_BASE = "https://context.reverso.net/translation"
CONJUGATOR_BASE = "https://conjugator.reverso.net"

# DrillCards keeps one page per word under its CEFR level, e.g.
# https://drillcards.org/de/words/b2/widersprechen — level and headword both
# lowercase.
DRILLCARDS_BASE = "https://drillcards.org/de/words"

# Letters only: 'Verb (trennbar)' and 'unregelmäßiges Verb' must both split
# into plain words before they can be recognised.
_WORDS = re.compile(r"[^\W\d_]+")


def context_url(card: WordCard) -> str:
    """Usage examples for the headword in Reverso Context."""
    return f"{CONTEXT_BASE}/german-{CONTEXT_LANGUAGE}/{_slug(card.wort)}"


def conjugation_url(card: WordCard) -> str | None:
    """The Reverso conjugation table, or None when the word is not a verb."""
    if not is_verb(card):
        return None
    return f"{CONJUGATOR_BASE}/conjugation-german-verb-{_slug(card.wort.lower())}.html"


def drillcards_url(card: WordCard) -> str:
    """The word's page on DrillCards, filed under its CEFR level."""
    return f"{DRILLCARDS_BASE}/{_slug(card.niveau.lower())}/{_slug(card.wort.lower())}"


def is_verb(card: WordCard) -> bool:
    """True for 'Verb', 'Hilfsverb', 'Modalverb' — but not for 'Adverb'.

    The word class comes from the model as free German text, so it is matched
    by suffix rather than by equality. 'Adverb' ends in the same four letters
    and is the one case that has to be excluded explicitly.
    """
    return any(
        token.endswith("verb") and token != "adverb"
        for token in (w.lower() for w in _WORDS.findall(card.wortart))
    )


def _slug(word: str) -> str:
    """Percent-encode the word: umlauts and ß are not URL-safe."""
    return quote(word.strip(), safe="")
