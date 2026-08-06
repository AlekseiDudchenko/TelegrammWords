# Wort des Tages — [@wunderwordsde](https://t.me/wunderwordsde)

A Telegram bot that posts a German word card twice a day: meanings, example
sentences, synonyms, antonyms and common collocations. The card is monolingual
— everything the reader sees is in German, except the English translation of
each example, which sits under a Telegram spoiler and is revealed by a tap.

Design notes and the reasoning behind the architecture: [PLAN.md](PLAN.md).

## How it works

GitHub Actions runs `python -m bot.main` on a schedule. The bot takes the next
unused word from `data/words.yml`, renders a card as an HTML message, sends it
to the channel, and commits `data/state.json` back to the repository.

The card comes from one of two places:

- **`data/cards.yml`** — 60 cards written by hand and checked into the
  repository. These are used first, in file order, so the first month runs
  without an API key and costs nothing.
- **The Claude API** — for every word that has no stored card. The reply is
  constrained by a strict JSON schema and validated before anything is sent.

```
bot/
  config.py     environment variables and paths
  models.py     WordCard schema + JSON Schema for structured outputs
  wordlist.py   loads data/words.yml
  cards.py      loads the pre-written cards from data/cards.yml
  state.py      picks a word without repeats, guards against double posting
  generator.py  Claude API call + response validation
  links.py      Reverso links + DrillCards, added only if the page exists
  formatter.py  WordCard -> HTML for Telegram
  telegram.py   sendMessage with retries
  main.py       CLI
```

## Running locally

```bash
pip install -r requirements-dev.txt
python -m pytest -q

# Print the finished message without sending it. No key needed for a word
# that has a stored card.
python -m bot.main --dry-run --word Fernweh

# A word outside data/cards.yml goes to the API
export ANTHROPIC_API_KEY=sk-ant-...
python -m bot.main --dry-run --word Trugschluss
```

Flags: `--dry-run`, `--word WORD`, `--level B2`, `--force`, `--verbose`.

## Setting up the live bot

1. Create a bot via [@BotFather](https://t.me/BotFather) → `TELEGRAM_BOT_TOKEN`.
2. Add the bot as an administrator of `@wunderwordsde` with permission to post.
3. Add the secrets under `Settings → Secrets and variables → Actions`:

   | Secret | Value | Required |
   |---|---|---|
   | `TELEGRAM_BOT_TOKEN` | token from BotFather | yes |
   | `TELEGRAM_CHAT_ID` | `@wunderwordsde` | no |
   | `ANTHROPIC_API_KEY` | key from console.anthropic.com | not for the first month |

`TELEGRAM_CHAT_ID` defaults to `@wunderwordsde` (see `bot/config.py`); a numeric
ID is only needed for a private channel. `ANTHROPIC_API_KEY` is only read once
the stored cards in `data/cards.yml` are used up — until then the run does not
touch the API at all. Without the key, the first run past the store fails with
exit code 2 and posts nothing.

To verify everything before the first scheduled run: `Actions → Wort des Tages →
Run workflow` with `dry_run` ticked. The card is written to the job log and
nothing is sent.

## Schedule

Two runs a day: `0 6 * * *` and `0 16 * * *` UTC — 08:00 and 18:00 Berlin time
in summer, an hour earlier in winter. GitHub Actions cron has no notion of
daylight saving time and does not guarantee the exact minute.

The double-post guard counts half-days rather than days. `data/state.json`
records the last slot posted (`"2026-08-04/pm"`), where the morning slot runs
until noon UTC and the evening slot after it. Both cron times sit hours away
from that boundary, so the delay Actions is known for cannot push a run into
the wrong half — and a re-run from the Actions UI, which replays an older slot,
stays silent.

## Adding words

Append to the appropriate section of `data/words.yml`. Order within the file
does not matter: the bot shuffles the list deterministically per cycle, so
adding words neither disturbs the current rotation nor causes repeats.

## Adding a pre-written card

Append an entry to `data/cards.yml`, keyed by the exact word from
`data/words.yml`. The card must fill every field of `WordCard`
(`bot/models.py`); `python -m pytest tests/test_cards.py` validates the whole
file, checks that each word exists in the word list at the same level, and
renders every card to catch broken markup. Order here *does* matter — stored
cards are posted top to bottom before anything is generated.

Then check the result: `python -m bot.main --dry-run --word <word>`.

Sixty cards are two posts a day for a month. `tests/test_cards.py` fails if the
store drops below that.

## Reverso links

Every card ends with a link to the word in [Reverso
Context](https://context.reverso.net/); verbs get a second link to their
conjugation table. Reverso Context works on a language pair; the other half is
`CONTEXT_LANGUAGE` in `bot/links.py` — `english`, to match the language of the
hidden example translations (`russian`, `french`, `spanish` … all work too).

## Language conventions

Code, comments, commit messages and documentation are English. German is used
only where it is the product itself: the words in `data/words.yml`, the labels
in the rendered card, and the `WordCard` field names, which mirror German
grammatical categories (`artikel`, `plural`, `stammformen`).

Inside a card, English appears in exactly one field: `beispiele_en`, the
translation of the example sentences. It needs one entry per sentence in
`beispiele`, in the same order — `WordCard` rejects the card otherwise, since
the formatter pairs the two lists by position.
