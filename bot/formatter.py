"""WordCard -> Telegram message (parse_mode=HTML).

The visible labels stay German: the card is meant to be read monolingually.
"""

from __future__ import annotations

from html import escape

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
        lines += ["", "✍️ <b>Beispiele</b>"]
        lines += [f"• <i>{e(sentence)}</i>" for sentence in card.beispiele]

    lines.append("")
    if card.synonyme:
        lines.append(f"🔗 <b>Synonyme:</b> {e(', '.join(card.synonyme))}")
    lines.append(
        f"↔️ <b>Antonyme:</b> {e(', '.join(card.antonyme)) if card.antonyme else '—'}"
    )
    if card.kollokationen:
        lines.append(f"💬 <b>Wendungen:</b> {e('; '.join(card.kollokationen))}")

    return "\n".join(lines).strip()


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
