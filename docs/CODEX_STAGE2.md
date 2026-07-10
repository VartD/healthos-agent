# Codex Stage 2 — эксплуатационный фундамент

Дата: 10 июля 2026

## Реализовано

- Alembic и initial schema migration.
- Удалён runtime `Base.metadata.create_all`.
- Docker Compose: PostgreSQL 16, backend, Telegram bot.
- Автоматическое применение migrations перед backend startup.
- `/health/live` и `/health/ready`.
- JSON request logging без query string и медицинских данных.
- GitHub Actions с PostgreSQL service.
- `pg_dump` backup, archive verification и guarded restore.
- Поддержка запуска тестов на SQLite или PostgreSQL через `TEST_DATABASE_URL`.

## Проверено в текущей среде

- 15/15 тестов.
- Python compilation.
- Alembic на SQLite: upgrade, current, downgrade, повторный upgrade.
- YAML parsing для Compose и GitHub Actions.
- Shell syntax backup/restore scripts.
- Чистота diff (`git diff --check`).

## Не проверено

- Docker image build и Compose runtime — Docker отсутствует.
- PostgreSQL migration/test job — выполнится после публикации GitHub branch.
- Telegram polling — нужен тестовый token и доступ к Telegram API.
- Backup/restore drill — нужен запущенный PostgreSQL container.

Непроверенные пункты нельзя считать завершёнными до получения фактических логов
и результатов команд.
