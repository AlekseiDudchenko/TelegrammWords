from datetime import datetime, timezone

import pytest

from bot import alert, watchdog
from bot.config import Config
from bot.state import State


@pytest.fixture
def sent(monkeypatch):
    """Capture what would have gone to Telegram."""
    calls = []

    def fake_send(token, chat_id, text):
        calls.append((token, chat_id, text))
        return 42

    monkeypatch.setattr(alert.telegram, "send_message", fake_send)
    return calls


def config(tmp_path, alert_chat="777", token="123:abc"):
    return Config(
        anthropic_api_key=None,
        telegram_bot_token=token,
        telegram_chat_id="@channel",
        telegram_alert_chat_id=alert_chat,
        model="claude-opus-5",
        data_dir=tmp_path,
    )


def test_alert_goes_to_the_private_chat_not_the_channel(tmp_path, sent):
    assert alert.send(config(tmp_path), "boom") is True
    (_, chat_id, text), = sent
    assert chat_id == "777"
    assert "boom" in text


def test_alert_is_dropped_when_no_chat_is_configured(tmp_path, sent):
    assert alert.send(config(tmp_path, alert_chat=None), "boom") is False
    assert sent == []


def test_alert_is_dropped_when_the_token_is_missing(tmp_path, sent):
    assert alert.send(config(tmp_path, token=None), "boom") is False
    assert sent == []


def test_alert_text_is_escaped(tmp_path, sent):
    # The channel messages use HTML parse mode, and so does this one.
    alert.send(config(tmp_path), "<not a tag> & more")
    assert "&lt;not a tag&gt; &amp; more" in sent[0][2]


def test_run_url_needs_both_variables(monkeypatch):
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "who/what")
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    assert alert.run_url() is None

    monkeypatch.setenv("GITHUB_RUN_ID", "9")
    assert alert.run_url() == "https://github.com/who/what/actions/runs/9"


def test_due_slot_looks_back_past_the_usual_delay():
    # 20:00 UTC, the evening check: the pm slot is what is owed.
    assert watchdog.due_slot(datetime(2026, 8, 6, 20, tzinfo=timezone.utc)) == (
        "2026-08-06/pm"
    )
    # 10:00 UTC, the morning check.
    assert watchdog.due_slot(datetime(2026, 8, 6, 10, tzinfo=timezone.utc)) == (
        "2026-08-06/am"
    )


def test_due_slot_survives_a_delayed_watchdog():
    # The watchdog is a scheduled run too and can be hours late. Looking back
    # from now keeps it pointing at the same slot instead of skipping ahead.
    late = datetime(2026, 8, 6, 17, tzinfo=timezone.utc)  # morning check, +7h
    assert watchdog.due_slot(late) == "2026-08-06/am"

    past_midnight = datetime(2026, 8, 7, 2, tzinfo=timezone.utc)  # evening, +6h
    assert watchdog.due_slot(past_midnight) == "2026-08-06/pm"


def test_watchdog_is_quiet_when_the_slot_was_served(tmp_path, sent, monkeypatch):
    _write_state(tmp_path, watchdog.due_slot(datetime.now(timezone.utc)))
    _env(monkeypatch, tmp_path)

    assert watchdog.main([]) == 0
    assert sent == []


def test_watchdog_reports_a_missing_post(tmp_path, sent, monkeypatch):
    _write_state(tmp_path, "2026-01-01/am")
    _env(monkeypatch, tmp_path)

    assert watchdog.main([]) == 1
    (_, chat_id, text), = sent
    assert chat_id == "777"
    assert "2026-01-01/am" in text


def test_watchdog_still_fails_when_alerting_is_unconfigured(
    tmp_path, sent, monkeypatch
):
    # No alert chat: the red run is then the only signal, so it must stay red.
    _write_state(tmp_path, "2026-01-01/am")
    _env(monkeypatch, tmp_path)
    monkeypatch.delenv("TELEGRAM_ALERT_CHAT_ID")

    assert watchdog.main([]) == 1
    assert sent == []


def _write_state(tmp_path, slot):
    State(last_post_slot=slot, posted=["alpha"]).save(tmp_path / "state.json")


def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("WORDS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_ALERT_CHAT_ID", "777")
