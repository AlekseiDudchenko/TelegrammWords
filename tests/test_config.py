import pytest

from bot.config import DEFAULT_CHAT_ID, DEFAULT_MODEL, Config, ConfigError

VARS = (
    "ANTHROPIC_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_ALERT_CHAT_ID",
    "ANTHROPIC_MODEL",
    "WORDS_DATA_DIR",
)


@pytest.fixture
def env(monkeypatch):
    for name in VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_apply_when_unset(env):
    config = Config.from_env()
    assert config.telegram_chat_id == DEFAULT_CHAT_ID
    assert config.model == DEFAULT_MODEL


def test_blank_variables_fall_back_to_defaults(env):
    # GitHub Actions substitutes an undefined secret with an empty string.
    for name in VARS:
        env.setenv(name, "")

    config = Config.from_env()
    assert config.telegram_chat_id == DEFAULT_CHAT_ID
    assert config.model == DEFAULT_MODEL
    assert config.anthropic_api_key is None
    assert config.telegram_bot_token is None
    assert config.telegram_alert_chat_id is None


def test_the_alert_chat_never_defaults_to_the_channel(env):
    # An alert must not reach the readers; without a private chat there is
    # simply nowhere to send it.
    assert Config.from_env().telegram_alert_chat_id is None

    env.setenv("TELEGRAM_ALERT_CHAT_ID", " 777 ")
    assert Config.from_env().telegram_alert_chat_id == "777"


def test_whitespace_is_treated_as_unset(env):
    env.setenv("TELEGRAM_CHAT_ID", "  ")
    assert Config.from_env().telegram_chat_id == DEFAULT_CHAT_ID


def test_values_are_stripped(env):
    env.setenv("TELEGRAM_CHAT_ID", " @somechannel\n")
    assert Config.from_env().telegram_chat_id == "@somechannel"


def test_blank_token_still_fails_require(env):
    env.setenv("TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(ConfigError):
        Config.from_env().require_telegram()


def test_require_telegram_returns_token_and_default_chat(env):
    env.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    assert Config.from_env().require_telegram() == ("123:abc", DEFAULT_CHAT_ID)
