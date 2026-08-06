"""WordCard -> Telegram message (parse_mode=HTML).

The visible labels stay German: the card is meant to be read monolingually.
The English translation of each example sits under a Telegram spoiler, so the
reader meets the German sentence first and only uncovers the translation after
trying it — a tap on the blurred line reveals it.
"""

from __future__ import annotations

from html import escape

from . import links
from .models import WordCard


def render(card: WordCard) -> str:
    """Build the message. Everything the model produced is HTML-escaped."""
    lines: list[str] = [f"🇩🇪 <b>Wort des Tages</b> · {e(card.niveau)}", ""]

    lines.append(f"<b>{e(_headword(card))}</b>  <code>[{e(card.ipa)}]</code>")
    subtitle = _subtitle(card)
    if subtitle:
        lines.append(f"<i>{e(subtitle)}</i>")

    lines.append("")
    lines.append("📖 <b>Bedeutung</b>")
    for i, meaning in enumerate(card.bedeutungen, start=1):
        prefix = f"{i}. " if len(card.bedeutungen) > 1 else ""
        lines.append(f"{prefix}{e(meaning)}")

    if card.beispiele:
        lines += ["", "✍️ <b>Beispiele</b> <i>· Übersetzung antippen</i>"]
        lines += _examples(card)

    lines.append("")
    if card.synonyme:
        lines.append(f"🔗 <b>Synonyme:</b> {e(', '.join(card.synonyme))}")
    lines.append(
        f"↔️ <b>Antonyme:</b> {e(', '.join(card.antonyme)) if card.antonyme else '—'}"
    )
    if card.kollokationen:
        lines.append(f"💬 <b>Wendungen:</b> {e('; '.join(card.kollokationen))}")

    lines += ["", f"🌐 <b>Reverso:</b> {_links(card)}"]
    lines.append(f"🃏 {_link(links.drillcards_url(card), 'Auf DrillCards üben')}")

    return "\n".join(lines).strip()


def _examples(card: WordCard) -> list[str]:
    """Each sentence, followed by its translation under a spoiler.

    Pairing by position is safe: `WordCard` rejects a card whose two lists
    differ in length, so the translation can never slip onto the wrong sentence.
    """
    lines: list[str] = []
    for sentence, translation in zip(card.beispiele, card.beispiele_en):
        lines.append(f"• <i>{e(sentence)}</i>")
        lines.append(f"   <tg-spoiler>{e(translation)}</tg-spoiler>")
    return lines


def _links(card: WordCard) -> str:
    """Reverso Context, plus the conjugation table when the word is a verb."""
    parts = [_link(links.context_url(card), "Kontext")]
    conjugation = links.conjugation_url(card)
    if conjugation:
        parts.append(_link(conjugation, "Konjugation"))
    return " · ".join(parts)


def _link(url: str, label: str) -> str:
    return f'<a href="{escape(url, quote=True)}">{e(label)}</a>'


def _headword(card: WordCard) -> str:
    """'das Haus, die Häuser', or just the word when there is no article."""
    parts = [f"{card.artikel} {card.wort}" if card.artikel else card.wort]
    if card.plural:
        parts.append(card.plural)
    return ", ".join(parts)


def _subtitle(card: WordCard) -> str:
    if card.stammformen:
        return f"{card.wortart} · {card.stammformen}"
    return card.wortart


def e(text: str) -> str:
    return escape(text, quote=False)
