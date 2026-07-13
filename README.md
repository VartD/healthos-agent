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
- безопасный свободный русский ввод событий без обязательных slash-команд;
- структурированный ввод давления и пульса с детерминированным red flag для
  значений ≥180/120;
- естественный утренний sleep check-in и подтверждение неоднозначных объёмов;
- 43 автоматизированных API/safety/bot/transport integration-теста;
- Alembic-миграции, live/readiness checks, JSON request logs;
- Docker Compose для PostgreSQL, backend и Telegram-бота;
- CI и backup/restore-скрипты.

## Чего нет

Mini App, мобильного приложения, LLM-оркестратора, Vision, голосового ввода,
автоматических напоминаний,
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

Реальная проверка backend + Telegram Bot API:

```bash
python scripts/smoke_real_services.py
# С явной отправкой одного сообщения:
python scripts/smoke_real_services.py --send-message
```

Второй вариант требует `TELEGRAM_SMOKE_CHAT_ID` в `.env`.

Подробности: [RUNBOOK](docs/RUNBOOK.md), [STATUS](docs/STATUS.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [BACKLOG](docs/BACKLOG.md),
[STAGE 4 ACCEPTANCE](docs/STAGE4_RELEASE_ACCEPTANCE.md).

Первый срез Stage 5: [FREE TEXT](docs/STAGE5_FREE_TEXT.md).
