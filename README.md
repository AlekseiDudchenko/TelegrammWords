# Wort des Tages — [@wunderwordsde](https://t.me/wunderwordsde)

A Telegram bot that posts one German word card per day: meanings, etymology,
example sentences, synonyms, antonyms and common collocations. The card itself
is monolingual — everything the reader sees is in German.

Design notes and the reasoning behind the architecture: [PLAN.md](PLAN.md).

## How it works

GitHub Actions runs `python -m bot.main` on a schedule. The bot takes the next
unused word from `data/words.yml`, asks Claude for a card constrained by a
strict JSON schema, renders it as an HTML message, sends it to the channel, and
commits `data/state.json` back to the repository.

```
bot/
  config.py     environment variables and paths
  models.py     WordCard schema + JSON Schema for structured outputs
  wordlist.py   loads data/words.yml
  state.py      picks a word without repeats, guards against double posting
  generator.py  Claude API call + response validation
  formatter.py  WordCard -> HTML for Telegram
  telegram.py   sendMessage with retries
  main.py       CLI
```

## Running locally

```bash
pip install -r requirements-dev.txt
python -m pytest -q

# Print the finished message without sending it (only ANTHROPIC_API_KEY needed)
export ANTHROPIC_API_KEY=sk-ant-...
python -m bot.main --dry-run --word Fernweh
```

Flags: `--dry-run`, `--word WORD`, `--level B2`, `--force`, `--verbose`.

## Setting up the live bot

1. Create a bot via [@BotFather](https://t.me/BotFather) → `TELEGRAM_BOT_TOKEN`.
2. Add the bot as an administrator of `@wunderwordsde` with permission to post.
3. Add the secrets under `Settings → Secrets and variables → Actions`:

   | Secret | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | key from console.anthropic.com |
   | `TELEGRAM_BOT_TOKEN` | token from BotFather |
   | `TELEGRAM_CHAT_ID` | `@wunderwordsde` |

`TELEGRAM_CHAT_ID` is optional — it defaults to `@wunderwordsde`
(see `bot/config.py`). A numeric ID is only needed for a private channel.

To verify everything before the first scheduled run: `Actions → Wort des Tages →
Run workflow` with `dry_run` ticked. The card is written to the job log and
nothing is sent.

## Schedule

`0 6 * * *` UTC — 08:00 Berlin time in summer, 07:00 in winter. GitHub Actions
cron has no notion of daylight saving time and does not guarantee the exact
minute.

## Adding words

Append to the appropriate section of `data/words.yml`. Order within the file
does not matter: the bot shuffles the list deterministically per cycle, so
adding words neither disturbs the current rotation nor causes repeats.

## Language conventions

Code, comments, commit messages and documentation are English. German is used
only where it is the product itself: the words in `data/words.yml`, the labels
in the rendered card, and the `WordCard` field names, which mirror German
grammatical categories (`artikel`, `plural`, `stammformen`).
