"""Outbound links for a word card.

Reverso first: the word in Reverso Context, and — for verbs only — its
conjugation table. Reverso Context always needs a language pair, so this is the
one place where the otherwise monolingual card points at a translation;
`CONTEXT_LANGUAGE` decides which one. Then DrillCards, where the same word can
be drilled; that link closes the post — but only once the page has been
confirmed to exist, since not every word of the list has one.

The Reverso URLs are built blind: they are search pages that answer for any
input. DrillCards is a page per word, so `resolve_drillcards` is the one
function here that goes to the network.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote, unquote

import httpx

from .models import WordCard

log = logging.getLogger(__name__)

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

# The existence check is on the critical path of a post, so it gets one short
# attempt: a link that cannot be confirmed in time is simply left out.
DRILLCARDS_TIMEOUT = 10.0

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
    """The word's page on DrillCards, filed under its CEFR level.

    The address the word would have; whether the page is really there is
    `resolve_drillcards`'s question.
    """
    return f"{DRILLCARDS_BASE}/{_slug(card.niveau.lower())}/{_slug(card.wort.lower())}"


def resolve_drillcards(card: WordCard) -> str | None:
    """The DrillCards URL if the page answers with 200, otherwise None.

    Anything short of a confirmed page — 404, a server error, a timeout, DNS
    trouble — means no link. A post missing one line is a much smaller problem
    than a post carrying a dead link, so every failure resolves the same way.
    """
    url = drillcards_url(card)
    try:
        response = httpx.head(url, timeout=DRILLCARDS_TIMEOUT, follow_redirects=True)
        # Some servers refuse HEAD outright; ask again properly before giving up.
        if response.status_code in (403, 405, 501):
            response = httpx.get(url, timeout=DRILLCARDS_TIMEOUT, follow_redirects=True)
    except httpx.HTTPError as exc:
        log.warning("DrillCards check for %s failed (%s) — link omitted.", url, exc)
        return None

    if response.status_code != 200:
        log.info("No DrillCards page for %s (HTTP %d).", url, response.status_code)
        return None

    # A 200 after being redirected elsewhere is the usual way a site says "no
    # such word": unknown pages land on the index or on a search page. Only a
    # final address still pointing at this word counts as a hit.
    if not _points_at(response.url, card.wort):
        log.info("DrillCards redirected %s to %s — link omitted.", url, response.url)
        return None

    return url


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


def _points_at(url: httpx.URL, word: str) -> bool:
    """True when the last path segment is still the word we asked for.

    The path comes back percent-encoded, and the encoding of an umlaut is not
    guaranteed to match ours byte for byte, so both sides are decoded first.
    """
    last = unquote(str(url.path)).rstrip("/").rsplit("/", 1)[-1]
    return last.casefold() == word.strip().casefold()


def _slug(word: str) -> str:
    """Percent-encode the word: umlauts and ß are not URL-safe."""
    return quote(word.strip(), safe="")
