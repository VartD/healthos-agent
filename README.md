# HealthOS Agent

Достоверная базовая версия HealthOS: закрытый FastAPI backend, PostgreSQL/SQLite,
Telegram-бот и детерминированный движок подсказок. Это ранний прототип, а не
готовая медицинская система.

## Что реализовано

- запись событий воды, глюкозы, мочевой кислоты, кофе, питания, тренировок,
  сауны и симптомов;
- защищённые API событий, профиля и модуля сна;
- простые режимы, risk flags и операционные подсказки;
- сервисная авторизация через `X-API-Key`;
- валидация базовых числовых значений;
- структурированный утренний sleep check-in и недельная сводка с одной NBA;
- Telegram-команды `/profile`, `/morning`, `/sleepweek`;
- 21 автоматизированный API/safety-тест;
- Alembic-миграции, live/readiness checks, JSON request logs;
- Docker Compose для PostgreSQL, backend и Telegram-бота;
- CI и backup/restore-скрипты.

## Чего нет

Mini App, мобильного приложения, LLM-агентов, Vision, автоматических напоминаний,
Digital Twin, Longevity Intelligence и полноценной пользовательской авторизации.

## Локальный запуск

```bash
cp .env.example .env
# Замените все placeholder-значения в .env.
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt -r bot/requirements.txt
cd backend
alembic upgrade head
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

## Docker Compose

После заполнения `.env`:

```bash
docker compose up --build -d
docker compose ps
```

Проверки состояния:

- `GET /health/live` — процесс backend работает;
- `GET /health/ready` — backend видит базу данных.

Резервное копирование:

```bash
./scripts/backup_postgres.sh
./scripts/verify_backup.sh backups/<file>.dump
```

Подробности: [RUNBOOK](docs/RUNBOOK.md), [STATUS](docs/STATUS.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [BACKLOG](docs/BACKLOG.md).
