"""Configuration read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data"

# The channel we post to. Telegram accepts @name directly as a chat_id; a
# numeric ID is only required for private channels.
DEFAULT_CHAT_ID = "@wunderwordsde"

DEFAULT_MODEL = "claude-opus-5"


class ConfigError(RuntimeError):
    """A required environment variable is missing."""


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str
    model: str
    data_dir: Path

    @property
    def words_file(self) -> Path:
        return self.data_dir / "words.yml"

    @property
    def state_file(self) -> Path:
        return self.data_dir / "state.json"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", DEFAULT_CHAT_ID),
            model=os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
            data_dir=Path(os.environ.get("WORDS_DATA_DIR", DEFAULT_DATA_DIR)),
        )

    def require_anthropic(self) -> str:
        if not self.anthropic_api_key:
            raise ConfigError(
                "ANTHROPIC_API_KEY is not set — no card can be generated without it."
            )
        return self.anthropic_api_key

    def require_telegram(self) -> tuple[str, str]:
        if not self.telegram_bot_token:
            raise ConfigError(
                "TELEGRAM_BOT_TOKEN is not set — use --dry-run to check the "
                "message format without sending."
            )
        if not self.telegram_chat_id:
            raise ConfigError("TELEGRAM_CHAT_ID is empty.")
        return self.telegram_bot_token, self.telegram_chat_id
