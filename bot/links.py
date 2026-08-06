"""Outbound links for a word card.

Reverso first: the word in Reverso Context, and — for verbs only — its
conjugation table. Reverso Context always needs a language pair, so this is the
one place where the otherwise monolingual card points at a translation;
`CONTEXT_LANGUAGE` decides which one. Then DrillCards, where the same word can
be drilled; that link closes the post — but only for a word DrillCards actually
has, which is a minority of this bot's list.

The Reverso URLs are built blind: they are search pages that answer for any
input. A DrillCards card is a real page that either exists or does not, so
`resolve_drillcards` looks the word up first — see below for why that lookup
cannot be an HTTP status check.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

import httpx

from .models import WordCard

log = logging.getLogger(__name__)

# The other half of the Reverso Context pair. English matches the language the
# hidden example translations are written in. Any language Reverso supports
# works here: english, russian, french, spanish …
CONTEXT_LANGUAGE = "english"

CONTEXT_BASE = "https://context.reverso.net/translation"
CONJUGATOR_BASE = "https://conjugator.reverso.net"

# DrillCards keeps one page per word under the deck it belongs to, e.g.
# https://drillcards.org/de/words/b2/widersprechen.
DRILLCARDS_BASE = "https://drillcards.org/de/words"

# Whether a word has a card is answered by this file, not by requesting the
# page. drillcards.org is a single-page app on GitHub Pages: every deep link is
# served by 404.html, which means /de/words/b2/widersprechen comes back with
# HTTP 404 even though the card is there. A status check would therefore drop
# every link. The index is a real static file — it answers 200 — and maps each
# word's slug to its deck.
DRILLCARDS_INDEX = "https://drillcards.org/data/word-index.json"

# The lookup is on the critical path of a post, so it gets one short attempt: a
# link that cannot be confirmed in time is simply left out.
DRILLCARDS_TIMEOUT = 10.0

# The site's own slug rules (src/client/word-slug.ts). Umlauts are
# transliterated rather than percent-encoded — 'üben' is 'ueben' — and the
# article is not part of the word.
_UMLAUTS = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
_ARTICLE = re.compile(r"^(der|die|das)\s+", re.IGNORECASE)
_NOT_SLUG = re.compile(r"[^a-z0-9]+")

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


def drillcards_slug(card: WordCard) -> str:
    """The headword as DrillCards spells it in a URL."""
    text = _ARTICLE.sub("", card.wort.strip()).lower()
    text = "".join(_UMLAUTS.get(char, char) for char in text)
    return _NOT_SLUG.sub("-", text).strip("-")


def resolve_drillcards(card: WordCard) -> str | None:
    """The word's DrillCards URL, or None when DrillCards does not have it.

    The deck comes from the index rather than from `card.niveau`: the two
    disagree often enough to matter — 'Haus' is A2 in this bot's list and sits
    in the a1 deck on DrillCards — and only the deck in the index makes a URL
    that resolves.

    A failed lookup — no such word, a bad response, a timeout, DNS trouble —
    means no link. A post missing one line is a much smaller problem than a
    post carrying a dead link, so every failure resolves the same way.
    """
    index = _word_index()
    if index is None:
        return None

    slug = drillcards_slug(card)
    deck = index.get(slug)
    if not isinstance(deck, str) or not deck:
        log.info("DrillCards has no card for '%s' — link omitted.", slug)
        return None

    return f"{DRILLCARDS_BASE}/{quote(deck, safe='')}/{quote(slug, safe='')}"


def _word_index() -> dict[str, object] | None:
    """The slug -> deck map DrillCards publishes, or None if it cannot be read."""
    try:
        response = httpx.get(
            DRILLCARDS_INDEX, timeout=DRILLCARDS_TIMEOUT, follow_redirects=True
        )
    except httpx.HTTPError as exc:
        log.warning("DrillCards index unreachable (%s) — link omitted.", exc)
        return None

    if response.status_code != 200:
        log.warning(
            "DrillCards index answered HTTP %d — link omitted.", response.status_code
        )
        return None

    try:
        index = response.json()
    except ValueError as exc:
        log.warning("DrillCards index is not valid JSON (%s) — link omitted.", exc)
        return None

    if not isinstance(index, dict):
        log.warning("DrillCards index is not an object — link omitted.")
        return None
    return index


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
