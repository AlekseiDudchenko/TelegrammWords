# TelegrammWords — "Wort des Tages"

A Telegram bot that posts one German word card per day: meanings, etymology,
examples, synonyms and antonyms. All explanations are in German (monolingual) —
a deliberate choice, since the card itself then doubles as reading practice.

## Decisions

| Question | Decision |
|---|---|
| Content | Claude API generates the card on the fly from a word in the list |
| Card language | German, monolingual |
| Scheduling | GitHub Actions cron, one run per day |
| Stack | Python 3.12 |
| Storage | Files in the repository (`data/`); state is committed back |

There is deliberately no database and no server: the load is one message a day,
and anything else would be infrastructure for its own sake.

## How it works

```
GitHub Actions (cron)
  └─ python -m bot.main
       ├─ state.py     → pick the next word (no repeats)
       ├─ generator.py → Claude API, structured output → WordCard
       ├─ formatter.py → HTML message for Telegram
       ├─ telegram.py  → sendMessage to the channel
       └─ state.py     → record word + date in data/state.json
  └─ commit & push data/state.json
```

## Repository layout

```
bot/
  __init__.py
  config.py      # environment variables, validated on startup
  models.py      # pydantic WordCard schema
  wordlist.py    # loads data/words.yml
  state.py       # data/state.json: word selection, double-post guard
  formatter.py   # WordCard → HTML
  telegram.py    # Bot API sendMessage
  main.py        # CLI: --dry-run, --word WORD, --force
data/
  words.yml      # word list tagged by level (A2/B1/B2/C1)
  state.json     # {"last_post_date": "2026-08-02", "cycle": 0, "posted": [...]}
tests/
  test_formatter.py, test_state.py, test_models.py, test_wordlist.py,
  test_generator.py
.github/workflows/
  daily.yml      # cron + manual dispatch
  tests.yml      # pytest on every push
```

## Card schema

Claude is called with a strict JSON schema and the reply is parsed into a
pydantic model — free-form text from the model is not accepted.

```python
class WordCard(BaseModel):
    wort: str                      # Haus
    artikel: str | None            # das — nouns only
    plural: str | None             # die Häuser
    stammformen: str | None        # verbs: gehen – ging – ist gegangen
    wortart: str                   # Substantiv / Verb / Adjektiv ...
    ipa: str                       # haʊ̯s
    niveau: str                    # A2 | B1 | B2 | C1
    bedeutungen: list[str]         # 1–3 definitions, in German
    etymologie: str                # 2–4 sentences: ahd./mhd./Latin roots
    beispiele: list[str]           # 2–3 sentences
    synonyme: list[str]            # 3–5
    antonyme: list[str]            # 0–4 (many words simply have none)
    kollokationen: list[str]       # 2–3 set phrases
```

Field names are German on purpose: they mirror German grammatical categories
and are part of the rendered card. `antonyme` deliberately allows an empty
list — forcing the model to produce an antonym for "Haus" is a reliable way to
get nonsense.

## Message format

`parse_mode=HTML`, not MarkdownV2 — escaping `.`, `-` and `!` there is a
standing source of bugs.

```
🇩🇪 Wort des Tages · B1

das Haus, die Häuser  [haʊ̯s]
Substantiv

📖 Bedeutung
1. Gebäude, in dem Menschen wohnen …
2. …

🌱 Herkunft
Von mhd. hūs, ahd. hūs …

✍️ Beispiele
• …
• …

🔗 Synonyme: Gebäude, Wohnhaus, Anwesen
↔️ Antonyme: —
💬 Wendungen: nach Hause gehen; das Haus hüten
```

## Reliability

- **Idempotence.** `state.json` stores `last_post_date`. A second run on the
  same day sends nothing — this covers double cron firings and manual
  "Run workflow" clicks. `--force` overrides it.
- **No repeated words.** Words are drawn from those not yet used; when the list
  is exhausted the cycle restarts with a new deterministic shuffle.
- **Response validation.** A schema violation triggers one retry, then fails the
  workflow. A silently malformed post cannot go out.
- **Order of operations.** Send first, then commit state with `pull --rebase`.
  If the commit fails, the next run sees the old date and posts a duplicate —
  hence the retry loop on push, and a failing job as the notification.
- **Secrets** live only in GitHub Secrets: `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`.
- **Dry run.** `python -m bot.main --dry-run --word Fernweh` prints the finished
  post and sends nothing. This is the main way to debug the format.

## Schedule

GitHub Actions cron runs in UTC and has no notion of daylight saving time.
`0 6 * * *` is 08:00 CEST in summer and 07:00 CET in winter, plus
`workflow_dispatch` for manual runs.

One platform quirk worth knowing: Actions cron does not guarantee the exact
minute — delays of 10–15 minutes under load are normal. For a word of the day
that does not matter.

## Cost

One request per day, ~1500 output tokens. Cents per month, in round numbers.

## Deliberately out of scope for v1

Left out to avoid needing a server and webhooks:

- interactive commands `/wort`, `/quiz` (require a long-running process);
- text-to-speech pronunciation;
- a weekly recap of the last seven words;
- reactions/polls for self-testing.

The first two only become cheap on a VPS — if we get to them, that is a
separate stage.
