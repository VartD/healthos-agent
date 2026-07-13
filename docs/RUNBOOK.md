# Инструкция по воспроизведению (Runbook)

Проект можно запустить локально с SQLite или через Docker Compose с PostgreSQL.
Локальный запуск, тесты и цикл Alembic `upgrade → downgrade → upgrade` проверены
Codex. Docker Compose с PostgreSQL, реальный Telegram polling, persistence после
перезапуска и restore drill проверены на deployment host 10 июля 2026 года.

## Вариант 1: Быстрый запуск с SQLite (Проверено)

Этот вариант идеален для разработки и тестирования.

1. **Клонирование и зависимости**
   ```bash
   git clone https://github.com/VartD/healthos-agent.git
   cd healthos-agent
   pip install -r backend/requirements.txt
   pip install -r bot/requirements.txt
   ```

2. **Настройка окружения**
   Создайте файл `.env` в корне проекта:
   ```env
   TELEGRAM_BOT_TOKEN=ваш_токен
   HEALTHOS_API_KEY=случайная_строка_минимум_32_символа
   HEALTHOS_TIMEZONE=Asia/Yekaterinburg
   BACKEND_URL=http://127.0.0.1:8000
   DATABASE_URL=sqlite:///./healthos.db
   ```

3. **Запуск Backend**
   ```bash
   cd backend
   alembic upgrade head
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   API будет доступно по адресу `http://127.0.0.1:8000/docs`. Схему создаёт
   выполненная перед запуском Alembic-миграция.

4. **Запуск Telegram-бота**
   В новом терминале:
   ```bash
   cd bot
   python telegram_bot.py
   ```

## Вариант 2: Docker Compose с PostgreSQL

1. **Настройка окружения**
   Создайте `.env` на основе `.env.example`. Обязательно задайте:

   - `TELEGRAM_BOT_TOKEN`;
   - `HEALTHOS_API_KEY` — случайная строка минимум 32 символа;
   - `POSTGRES_PASSWORD` — длинный пароль без символов, требующих URL-encoding;
   - `HEALTHOS_TIMEZONE`.

2. **Запуск**
   ```bash
   docker compose up --build -d
   ```
   Это поднимает PostgreSQL, применяет Alembic-миграции, запускает backend и после
   успешного readiness check запускает Telegram-бота.

   Текущий deployment использует Linux `network_mode: host`, потому что в среде
   Manus недоступна обычная Docker bridge-сеть. PostgreSQL и backend явно
   привязаны к `127.0.0.1`; не меняйте их bind-адреса без firewall/TLS proxy.

3. **Проверка**
   ```bash
   docker compose ps
   curl http://127.0.0.1:8000/health/live
   curl http://127.0.0.1:8000/health/ready
   ```

## Автоматизированное тестирование

Из корня репозитория:

```bash
pytest
```

Реализовано 26 тестов API, авторизации, фильтрации, валидации, safety,
Telegram handlers и aiohttp transport. Bot integration-тест использует настоящий
FastAPI/DB-контур и имитирует только внешний Telegram transport; отдельный реальный
Telegram и Docker E2E также пройден.

## Миграции

Из каталога `backend/`:

```bash
alembic current
alembic upgrade head
```

Не используйте `Base.metadata.create_all` для production-схемы.

## Backup и restore

```bash
./scripts/backup_postgres.sh
./scripts/verify_backup.sh backups/<file>.dump
CONFIRM_RESTORE=YES ./scripts/restore_postgres.sh backups/<file>.dump
```

Restore является разрушительной операцией и требует явной переменной
`CONFIRM_RESTORE=YES`. Выполняйте drill только во временной БД/volume. Первый drill
успешно пройден 10 июля 2026 года без воздействия на production.

## Проверенный и непроверенный контур

- Проверено: Python compilation, 26 тестов, SQLite API, Alembic на SQLite, синтаксис
  YAML и shell-скриптов, реальный Telegram, Docker/PostgreSQL, restart и restore.
- Будет проверено после публикации: GitHub Actions с PostgreSQL.
- Требует повторного короткого smoke: текущий HEAD после bind/import hardening.

## Telegram-сценарий «Сон»

```text
/profile 8 Asia/Yekaterinburg
/morning 7.5 4 1 3 комментарий
/sleepweek
```

Параметры `/morning`: часы сна, качество 1–5, число пробуждений, энергия 1–5,
необязательный комментарий. Повторный чекин за ту же локальную дату обновляет
существующую запись.

## Реальный smoke-тест Telegram

После запуска backend и заполнения `.env`:

```bash
python scripts/smoke_real_services.py
```

Без изменения данных скрипт проверяет backend live/readiness, защищённый API,
Telegram `getMe` и отсутствие webhook для polling-режима.

Для явной отправки одного тестового сообщения задайте `TELEGRAM_SMOKE_CHAT_ID` и
выполните:

```bash
python scripts/smoke_real_services.py --send-message
```

Скрипт никогда не выводит токен или API-key.
