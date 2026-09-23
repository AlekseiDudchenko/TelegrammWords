# Kollokation des Tages — [@wunderwordsde](https://t.me/wunderwordsde)

A Telegram bot that posts one German collocation every morning. Each card has a
short German explanation, two example sentences with hidden English translations,
and a usage note. Published word cards remain in `data/cards.yml` as an archive.

The original word-card design is described in [PLAN.md](PLAN.md).

## Daily posts

GitHub Actions runs `python -m bot.main` at 08:00 `Europe/Berlin`. All 60
collocations are also listed by level in `data/words.yml`. The bot checks each
card against that list, takes the next unposted card from `data/collocations.yml`
in file order, sends the HTML message to Telegram, and commits the updated
`data/state.json`. There are 60
collocations, enough for 60 daily posts without an AI API key. Once all 60 are
posted, the job fails with a clear message and sends nothing until more cards
are added. It does not silently return to unused single-word entries.

The card includes a Reverso Context search link. Collocation posts omit the
DrillCards link; the phrase does not need to exist in the app.

`last_post_date` in `data/state.json` prevents a second post on the same Berlin
calendar day. A manual `--force` run can override this guard.

## Add a collocation

Add the expression under its level in `data/words.yml`, then append a matching
mapping entry to `data/collocations.yml`. Its key must exactly
match `ausdruck`. Required fields are `ausdruck`, `niveau`, `bedeutung`, two
`beispiele`, their two `beispiele_en` translations, and `gebrauch`. The only
English in a card goes into `beispiele_en`; those lines appear behind Telegram
spoilers. Entries publish in file order and must not duplicate an earlier phrase.

Check the file with `python -m pytest -q`, then preview the next post with
`python -m bot.main --dry-run`. A dry run does not send or save anything.

## Setup

1. Add the bot as an administrator of `@wunderwordsde` with permission to post.
2. Add `TELEGRAM_BOT_TOKEN` under GitHub `Settings → Secrets and variables → Actions`.
3. Optionally set `TELEGRAM_CHAT_ID`; it defaults to `@wunderwordsde`.

`ANTHROPIC_API_KEY` is not used for scheduled collocation posts. The original
`--word WORD` option can preview a listed collocation or request a word card;
an unstored word would still require that API key. `--dry-run`, `--force`, and
`--level` also remain available for manual runs.

GitHub Actions schedules 08:00 in the `Europe/Berlin` timezone, including
daylight saving time. GitHub may start a scheduled job a little late.
