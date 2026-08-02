# TelegrammWords — «Wort des Tages»

Телеграм-бот, который раз в день публикует карточку немецкого слова: значение,
этимология, примеры, синонимы и антонимы. Все пояснения — на немецком
(einsprachig), это осознанное решение: карточка сама по себе тренирует
Leseverstehen.

## Принятые решения

| Вопрос | Решение |
|---|---|
| Контент | Claude API генерирует карточку на лету по слову из списка |
| Язык карточки | Немецкий, einsprachig |
| Запуск | GitHub Actions cron, один прогон в сутки |
| Стек | Python 3.12 |
| Хранилище | Файлы в репозитории (`data/`), состояние коммитится обратно |

Отдельной БД и сервера нет намеренно: нагрузка — одно сообщение в сутки,
всё остальное было бы лишней инфраструктурой.

## Как это работает

```
GitHub Actions (cron)
  └─ python -m bot.main
       ├─ state.py     → выбрать следующее слово (без повторов)
       ├─ generator.py → Claude API, structured output → WordCard
       ├─ formatter.py → HTML-сообщение для Telegram
       ├─ telegram.py  → sendMessage в канал
       └─ state.py     → записать слово + дату в data/state.json
  └─ commit & push data/state.json
```

## Структура репозитория

```
bot/
  __init__.py
  config.py      # чтение env, валидация на старте
  models.py      # pydantic-схема WordCard
  wordlist.py    # загрузка data/words.yml
  state.py       # data/state.json: выбор слова, защита от дублей
  generator.py   # вызов Claude API
  formatter.py   # WordCard → HTML
  telegram.py    # Bot API sendMessage
  main.py        # CLI: --dry-run, --word WORT, --force
data/
  words.yml      # список слов с уровнем (A2/B1/B2/C1)
  state.json     # {"posted": [...], "last_post_date": "2026-08-02"}
tests/
  test_formatter.py, test_state.py, test_models.py
.github/workflows/
  daily.yml      # cron + ручной запуск
```

## Схема карточки

Claude вызывается с `tools` и жёстким `input_schema`, ответ парсится в pydantic —
свободного текста от модели мы не принимаем.

```python
class WordCard(BaseModel):
    wort: str                      # Haus
    artikel: str | None            # das — для существительных
    plural: str | None             # Häuser
    stammformen: str | None        # для глаголов: geht – ging – ist gegangen
    wortart: str                   # Substantiv / Verb / Adjektiv ...
    ipa: str                       # [haʊ̯s]
    niveau: str                    # A2 | B1 | B2 | C1
    bedeutungen: list[str]         # 1–3 определения на немецком
    etymologie: str                # 2–4 предложения: ahd./mhd./lat. корни
    beispiele: list[str]           # 2–3 предложения
    synonyme: list[str]            # 3–5
    antonyme: list[str]            # 0–4 (у многих слов их просто нет)
    kollokationen: list[str]       # 2–3 устойчивых сочетания
```

`antonyme` намеренно допускает пустой список: заставлять модель выдумывать
антоним к «Haus» — верный способ получить мусор.

## Формат поста

`parse_mode=HTML` (не MarkdownV2 — там экранирование `.`, `-`, `!` превращается
в источник багов).

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

## Надёжность

- **Идемпотентность.** `state.json` хранит `last_post_date`. Повторный прогон в
  тот же день ничего не отправляет — защита от двойного срабатывания cron и от
  ручного «Run workflow». Обходится флагом `--force`.
- **Без повторов слов.** Слово берётся из ещё не использованных; когда список
  исчерпан — цикл начинается заново с новым перемешиванием.
- **Валидация ответа модели.** Ошибка схемы → один повторный запрос → падение
  workflow. Молча кривой пост не выйдет.
- **Порядок операций.** Сначала отправка, потом коммит состояния с
  `pull --rebase`. Если коммит не прошёл, следующий прогон увидит старую дату и
  отправит дубль — поэтому push состояния идёт с ретраями, а падение workflow
  приходит уведомлением на почту.
- **Секреты** — только GitHub Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
  `ANTHROPIC_API_KEY`.
- **Dry-run.** `python -m bot.main --dry-run --word Fernweh` печатает готовый
  пост в консоль, ничего не отправляя. Основной способ отладки формата.

## Расписание

Cron в GitHub Actions работает по UTC, летнего времени не знает. `0 6 * * *` —
это 08:00 CEST летом и 07:00 CET зимой. Плюс `workflow_dispatch` для ручного
запуска.

Важная особенность платформы: cron в Actions не гарантирует точное время,
задержка до 10–15 минут при высокой нагрузке — норма. Для «слова дня» это
неважно.

## Стоимость

Один запрос в сутки, ~1500 выходных токенов. Порядок величины — центы в месяц.

## Что делаем не сейчас

Осознанно вне первой версии, чтобы не тащить сервер и вебхуки:

- интерактивные команды `/wort`, `/quiz` (требуют постоянно работающий процесс);
- озвучка слова через TTS;
- еженедельная сводка-повторение из 7 слов;
- реакции/опросы для самопроверки.

Первые две «дешевеют» только при переезде на VPS — если дойдём до них, это
отдельный этап.

## План работ

1. Каркас пакета, `config.py`, `models.py` + тесты схемы.
2. `data/words.yml` — стартовые ~200 слов с разметкой по уровням.
3. `generator.py`: Claude API со structured output, ретрай на невалидный ответ.
4. `formatter.py` + `telegram.py`, экранирование HTML, тесты рендера.
5. `state.py`: выбор слова, дедупликация, защита от повторной публикации.
6. `main.py` с `--dry-run` / `--word` / `--force`.
7. `.github/workflows/daily.yml` + README с инструкцией по секретам.
