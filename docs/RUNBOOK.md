# Инструкция по воспроизведению (Runbook)

Проект можно запустить локально с SQLite или через Docker Compose с PostgreSQL.
Локальный запуск, тесты и цикл Alembic `upgrade → downgrade → upgrade` проверены
Codex. Docker Compose статически проверен, но фактически не запускался: Docker в
текущей среде отсутствует.

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

На этапах Codex P0–P2 реализован 21 тест API, авторизации, фильтрации пользователей,
валидации и safety-логики. Telegram polling и Docker Compose пока требуют отдельной
интеграционной проверки.

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
`CONFIRM_RESTORE=YES`. Фактический backup/restore drill должен быть выполнен в
Docker-среде до первого пилота.

## Проверенный и непроверенный контур

- Проверено: Python compilation, 21 тест, SQLite API, Alembic на SQLite, синтаксис
  YAML и shell-скриптов.
- Будет проверено после публикации: GitHub Actions с PostgreSQL.
- Не проверено фактическим запуском: Docker Compose, Telegram polling,
  PostgreSQL backup/restore.

## Telegram-сценарий «Сон»

```text
/profile 8 Asia/Yekaterinburg
/morning 7.5 4 1 3 комментарий
/sleepweek
```

Параметры `/morning`: часы сна, качество 1–5, число пробуждений, энергия 1–5,
необязательный комментарий. Повторный чекин за ту же локальную дату обновляет
существующую запись.
