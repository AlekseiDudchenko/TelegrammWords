from bot import audio, collocations, main, telegram
from bot.config import DEFAULT_DATA_DIR
from bot.state import State


def _store():
    return collocations.load(DEFAULT_DATA_DIR / "collocations.yml")


def test_every_unpublished_collocation_has_a_recording():
    posted = State.load(DEFAULT_DATA_DIR / "state.json").posted
    missing = [
        card.ausdruck
        for card in audio.unpublished(_store(), posted)
        if audio.find(DEFAULT_DATA_DIR / "audio", card) is None
    ]
    assert missing == [], "run python -m bot.audio"


def test_published_cards_need_no_recording():
    store = _store()
    first = next(iter(store))
    left = audio.unpublished(store, [f"collocation:{first}"])
    assert first not in {card.ausdruck for card in left}
    assert len(left) == len(store) - 1


def test_an_edited_text_no_longer_matches_its_recording():
    card = next(iter(_store().values()))
    for field, value in [
        ("beispiele", [card.beispiele[0] + " Heute.", *card.beispiele[1:]]),
        ("bedeutung", card.bedeutung + " Heute."),
        ("ausdruck", card.ausdruck + " heute"),
    ]:
        edited = card.model_copy(update={field: value})
        assert audio.key(audio.segments(card)) != audio.key(audio.segments(edited))
    assert audio.key(audio.segments(card)) == audio.key(audio.segments(card.model_copy()))


def test_recording_reads_phrase_definition_and_examples_with_labels_in_own_voice():
    card = next(iter(_store().values()))
    parts = audio.segments(card)
    assert [text for _, text in parts] == [
        card.ausdruck, "Bedeutung", card.bedeutung, "Beispiele", *card.beispiele,
    ]
    assert {voice for voice, text in parts if text in {"Bedeutung", "Beispiele"}} == {
        audio.LABEL_VOICE
    }
    assert audio.LABEL_VOICE != audio.VOICE


def _run_send(monkeypatch, tmp_path, voice):
    recording = tmp_path / "x.ogg"
    recording.write_bytes(b"OggS")
    saved = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setattr(main.State, "load", lambda _: State())
    monkeypatch.setattr(main.State, "save", lambda self, _: saved.append(self.posted))
    monkeypatch.setattr(main.audio, "find", lambda *_: recording)
    monkeypatch.setattr(main.telegram, "send_message", lambda *a: 42)
    monkeypatch.setattr(main.telegram, "send_voice", voice)
    return main.main([]), saved, recording


def test_voice_reply_follows_the_post(monkeypatch, tmp_path):
    calls = []

    def voice(token, chat_id, path, reply_to=None, caption=None):
        calls.append((path, reply_to))
        return 43

    code, saved, recording = _run_send(monkeypatch, tmp_path, voice)
    assert code == 0
    assert calls == [(recording, 42)]
    assert saved == [["collocation:eine Entscheidung treffen"]]


def test_failed_voice_reply_still_saves_the_state(monkeypatch, tmp_path):
    def voice(*a, **k):
        raise telegram.TelegramError("boom")

    code, saved, _ = _run_send(monkeypatch, tmp_path, voice)
    assert code == 0
    assert saved == [["collocation:eine Entscheidung treffen"]]


def test_dry_run_names_the_recording(monkeypatch, capsys):
    monkeypatch.setattr(main.State, "load", lambda _: State())
    monkeypatch.setattr(main.audio, "find", lambda *_: DEFAULT_DATA_DIR / "audio" / "a.ogg")
    assert main.main(["--dry-run"]) == 0
    assert "[voice reply:" in capsys.readouterr().out
