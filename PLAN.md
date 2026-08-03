# TelegrammWords — "Wort des Tages"

A Telegram bot that posts a German word card twice a day: meanings, examples,
synonyms and antonyms. All explanations are in German (monolingual) —
a deliberate choice, since the card itself then doubles as reading practice.

## Decisions

| Question | Decision |
|---|---|
| Content | 60 cards written by hand in the repository; the Claude API takes over once they run out |
| Card language | German, monolingual |
| Scheduling | GitHub Actions cron, two runs per day |
| Stack | Python 3.12 |
| Storage | Files in the repository (`data/`); state is committed back |

There is deliberately no database and no server: the load is two messages a
day, and anything else would be infrastructure for its own sake.

## How it works

```
GitHub Actions (cron)
  └─ python -m bot.main
       ├─ cards.py     → load the pre-written cards
       ├─ state.py     → pick the next word (stored cards first, no repeats)
       ├─ cards.yml    → use the stored card …
       │   └─ generator.py → … or, if there is none, Claude API → WordCard
       ├─ formatter.py → HTML message for Telegram
       ├─ telegram.py  → sendMessage to the channel
       └─ state.py     → record word + slot in data/state.json
  └─ commit & push data/state.json
```

The store exists for two reasons. The channel's first month is its shop
window, and hand-written cards are simply better than generated ones —
definitions and examples chosen for the word rather than for the schema. And it
decouples going live from having an API key: the bot can start posting with
nothing but a Telegram token.

Both paths end in the same `WordCard`, so `cards.yml` is validated against the
same schema the API is constrained by. A card that would break the format
fails in CI, not in the channel.

## Repository layout

```
bot/
  __init__.py
  config.py      # environment variables, validated on startup
  models.py      # pydantic WordCard schema
  wordlist.py    # loads data/words.yml
  cards.py       # loads data/cards.yml, validated against WordCard
  state.py       # data/state.json: word selection, double-post guard
  formatter.py   # WordCard → HTML
  telegram.py    # Bot API sendMessage
  main.py        # CLI: --dry-run, --word WORD, --force
data/
  words.yml      # word list tagged by level (A2/B1/B2/C1)
  cards.yml      # 60 pre-written cards, posted in file order
  state.json     # {"last_post_slot": "2026-08-02/pm", "cycle": 0, "posted": [...]}
tests/
  test_formatter.py, test_state.py, test_models.py, test_wordlist.py,
  test_cards.py, test_generator.py, test_config.py
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

✍️ Beispiele
• …
• …

🔗 Synonyme: Gebäude, Wohnhaus, Anwesen
↔️ Antonyme: —
💬 Wendungen: nach Hause gehen; das Haus hüten
```

## Reliability

- **Idempotence.** `state.json` stores `last_post_slot` — the half-day last
  served, e.g. `"2026-08-02/pm"`. A second run in the same slot sends nothing,
  which covers double cron firings and manual "Run workflow" clicks; the guard
  also rejects *earlier* slots, so re-running yesterday's job from the Actions
  UI is silent too. `--force` overrides it.
- **No repeated words.** Words are drawn from those not yet used; when the list
  is exhausted the cycle restarts with a new deterministic shuffle. Words with
  a stored card come first, in the order of `cards.yml` — including in later
  cycles, which is deliberate: a hand-written card is the better post and it
  costs nothing.
- **Response validation.** A schema violation triggers one retry, then fails the
  workflow. A silently malformed post cannot go out.
- **Order of operations.** Send first, then commit state with `pull --rebase`.
  If the commit fails, the next run sees the old date and posts a duplicate —
  hence the retry loop on push, and a failing job as the notification.
- **Secrets** live only in GitHub Secrets: `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`. Only the first is needed while the
  stored cards last.
- **Dry run.** `python -m bot.main --dry-run --word Fernweh` prints the finished
  post and sends nothing. This is the main way to debug the format.

## Schedule

GitHub Actions cron runs in UTC and has no notion of daylight saving time.
`0 6 * * *` and `0 16 * * *` are 08:00 and 18:00 CEST in summer, an hour
earlier in winter, plus `workflow_dispatch` for manual runs.

One platform quirk worth knowing: Actions cron does not guarantee the exact
minute — delays of 10–15 minutes under load are normal. That quirk is why the
two slots are split at noon UTC rather than at the cron times themselves: each
run has six hours of slack before it could be mistaken for the other one.

## Cost

Nothing for the first month — those cards are in the repository. After that two
requests a day, ~1500 output tokens each: still cents per month, in round
numbers.

## Deliberately out of scope for v1

Left out to avoid needing a server and webhooks:

- interactive commands `/wort`, `/quiz` (require a long-running process);
- text-to-speech pronunciation;
- a weekly recap of the last seven words;
- reactions/polls for self-testing.

The first two only become cheap on a VPS — if we get to them, that is a
separate stage.
