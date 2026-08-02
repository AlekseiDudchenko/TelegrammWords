# Wort des Tages — [@wunderwordsde](https://t.me/wunderwordsde)

Телеграм-бот, который раз в день публикует карточку немецкого слова: значение,
этимология, примеры, синонимы, антонимы и устойчивые сочетания. Всё —
einsprachig, на немецком.

План и обоснование архитектурных решений: [PLAN.md](PLAN.md).

## Как это работает

GitHub Actions по крону запускает `python -m bot.main`. Бот берёт следующее
неиспользованное слово из `data/words.yml`, просит Claude сгенерировать карточку
по жёсткой JSON-схеме, рендерит её в HTML-сообщение, отправляет в канал и
коммитит `data/state.json` обратно в репозиторий.

```
bot/
  config.py     env-переменные и пути
  models.py     схема WordCard + JSON Schema для structured outputs
  wordlist.py   загрузка data/words.yml
  state.py      выбор слова без повторов, защита от двойной публикации
  generator.py  вызов Claude API + валидация ответа
  formatter.py  WordCard -> HTML для Telegram
  telegram.py   sendMessage с ретраями
  main.py       CLI
```

## Локальный запуск

```bash
pip install -r requirements-dev.txt
python -m pytest -q

# Посмотреть готовое сообщение, ничего не отправляя (нужен только ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
python -m bot.main --dry-run --word Fernweh
```

Флаги: `--dry-run`, `--word WORT`, `--niveau B2`, `--force`, `--verbose`.

## Что нужно настроить для боевого запуска

1. Создать бота через [@BotFather](https://t.me/BotFather) → `TELEGRAM_BOT_TOKEN`.
2. Добавить бота администратором канала `@wunderwordsde` с правом публикации.
3. В `Settings → Secrets and variables → Actions` репозитория добавить секреты:

   | Секрет | Значение |
   |---|---|
   | `ANTHROPIC_API_KEY` | ключ из console.anthropic.com |
   | `TELEGRAM_BOT_TOKEN` | токен от BotFather |
   | `TELEGRAM_CHAT_ID` | `@wunderwordsde` |

`TELEGRAM_CHAT_ID` можно не задавать — по умолчанию используется
`@wunderwordsde` (см. `bot/config.py`). Числовой ID нужен только для приватного
канала.

Проверить всё до первого крона: `Actions → Wort des Tages → Run workflow`,
поставив галочку `dry_run` — карточка появится в логе, ничего не отправится.

## Расписание

`0 6 * * *` UTC — 08:00 по Берлину летом, 07:00 зимой. Cron в GitHub Actions не
знает про переход на летнее время и не гарантирует точную минуту запуска.

## Добавить слова

Дописать в нужную секцию `data/words.yml`. Порядок внутри файла не важен: бот
перемешивает список детерминированно по номеру цикла, так что добавление слов
не ломает текущую очередь и не приводит к повторам.
