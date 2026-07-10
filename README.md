# HealthOS Agent

Достоверная базовая версия HealthOS: закрытый FastAPI backend, PostgreSQL/SQLite,
Telegram-бот и детерминированный движок подсказок. Это ранний прототип, а не
готовая медицинская система.

## Что реализовано

- запись событий воды, глюкозы, мочевой кислоты, кофе, питания, тренировок,
  сауны и симптомов;
- три защищённые API-операции: `POST /events`, `GET /events`, `GET /analyze`;
- простые режимы, risk flags и операционные подсказки;
- сервисная авторизация через `X-API-Key`;
- валидация базовых числовых значений;
- 13 автоматизированных API/safety-тестов.

## Чего нет

Mini App, мобильного приложения, LLM-агентов, Vision, APScheduler, Digital Twin,
Longevity Intelligence и полноценной пользовательской авторизации.

## Локальный запуск

```bash
cp .env.example .env
# Замените все placeholder-значения в .env.
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt -r bot/requirements.txt
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

В другом терминале:

```bash
. .venv/bin/activate
cd bot
python telegram_bot.py
```

## Тесты

```bash
pytest
```

Подробности: [RUNBOOK](docs/RUNBOOK.md), [STATUS](docs/STATUS.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [BACKLOG](docs/BACKLOG.md).
