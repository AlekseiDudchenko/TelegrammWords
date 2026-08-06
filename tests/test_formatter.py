from bot.formatter import render
from bot.models import WordCard

HAUS = WordCard(
    wort="Haus",
    artikel="das",
    plural="die Häuser",
    stammformen=None,
    wortart="Substantiv",
    ipa="haʊ̯s",
    niveau="A2",
    bedeutungen=["Gebäude, in dem Menschen wohnen."],
    beispiele=["Wir wohnen in einem alten Haus."],
    beispiele_en=["We live in an old house."],
    synonyme=["Gebäude", "Wohnhaus"],
    antonyme=[],
    kollokationen=["nach Hause gehen"],
)


def test_headword_shows_article_and_plural():
    assert "das Haus, die Häuser" in render(HAUS)


def test_empty_antonyms_render_as_dash():
    assert "↔️ <b>Antonyme:</b> —" in render(HAUS)


def test_verb_shows_principal_parts_instead_of_article():
    card = HAUS.model_copy(
        update={
            "wort": "gehen",
            "artikel": None,
            "plural": None,
            "wortart": "Verb",
            "stammformen": "gehen – ging – ist gegangen",
        }
    )
    out = render(card)
    assert "<b>gehen</b>" in out
    assert "Verb · gehen – ging – ist gegangen" in out


def test_model_text_is_html_escaped():
    card = HAUS.model_copy(update={"bedeutungen": ["Zeichen < und > und &"]})
    out = render(card)
    assert "Zeichen &lt; und &gt; und &amp;" in out
    # The template's own tags survive.
    assert "<b>Wort des Tages</b>" in out


def test_context_link_is_always_there():
    out = render(HAUS)
    assert '<a href="https://context.reverso.net/translation/german-' in out
    assert ">Kontext</a>" in out


def test_only_verbs_get_a_conjugation_link():
    assert "Konjugation" not in render(HAUS)

    verb = HAUS.model_copy(update={"wort": "gehen", "wortart": "Verb"})
    out = render(verb)
    assert (
        '<a href="https://conjugator.reverso.net/conjugation-german-verb-gehen.html">'
        "Konjugation</a>" in out
    )


def test_drillcards_link_closes_the_post():
    out = render(HAUS, drillcards="https://drillcards.org/de/words/a2/haus")
    assert out.endswith(
        '🃏 <a href="https://drillcards.org/de/words/a2/haus">Auf DrillCards üben</a>'
    )


def test_without_a_drillcards_link_the_post_ends_with_reverso():
    out = render(HAUS)
    assert "DrillCards" not in out
    assert out.rstrip().endswith("</a>")
    assert "🌐 <b>Reverso:</b>" in out.splitlines()[-1]


def test_umlauts_in_links_are_percent_encoded():
    out = render(HAUS.model_copy(update={"wort": "üben", "wortart": "Verb"}))
    assert "german-verb-%C3%BCben.html" in out
    assert "/%C3%BCben\"" in out


def test_translation_is_hidden_behind_a_spoiler():
    out = render(HAUS)
    assert "• <i>Wir wohnen in einem alten Haus.</i>" in out
    assert "<tg-spoiler>We live in an old house.</tg-spoiler>" in out
    # The translation follows its own sentence, never precedes it.
    assert out.index("Wir wohnen") < out.index("We live")


def test_every_example_gets_its_own_spoiler():
    card = HAUS.model_copy(
        update={
            "beispiele": ["Das Haus ist alt.", "Das Haus steht leer."],
            "beispiele_en": ["The house is old.", "The house stands empty."],
        }
    )
    assert render(card).count("<tg-spoiler>") == 2


def test_translations_are_html_escaped():
    card = HAUS.model_copy(update={"beispiele_en": ["Bread & butter <here>"]})
    out = render(card)
    assert "<tg-spoiler>Bread &amp; butter &lt;here&gt;</tg-spoiler>" in out


def test_multiple_meanings_are_numbered():
    card = HAUS.model_copy(update={"bedeutungen": ["Erste Bedeutung.", "Zweite."]})
    out = render(card)
    assert "1. Erste Bedeutung." in out
    assert "2. Zweite." in out
