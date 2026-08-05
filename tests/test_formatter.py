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


def test_umlauts_in_links_are_percent_encoded():
    out = render(HAUS.model_copy(update={"wort": "üben", "wortart": "Verb"}))
    assert "german-verb-%C3%BCben.html" in out
    assert "/%C3%BCben\"" in out


def test_multiple_meanings_are_numbered():
    card = HAUS.model_copy(update={"bedeutungen": ["Erste Bedeutung.", "Zweite."]})
    out = render(card)
    assert "1. Erste Bedeutung." in out
    assert "2. Zweite." in out
