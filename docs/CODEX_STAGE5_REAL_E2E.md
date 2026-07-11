# Real Telegram E2E и эксплуатационная приёмка Stage 4

Дата: 10 июля 2026

## Подтверждённый сценарий

1. Существующий Telegram-бот ответил на `/start` и показал команды Stage 4.
2. `/profile 8 Asia/Yekaterinburg` сохранил цель 8 часов и timezone.
3. `/morning 7.5 4 1 3 тестовый чекин` сохранил структурированный sleep check-in.
4. `/sleepweek` вернул 1/7, 7.5 часа, качество 4/5, энергию 3/5 и одну NBA.
5. `/status` вернул режим NORMAL, risk/effect/prediction/commands.

## Что это доказывает

- реальный Telegram Bot API и polling;
- актуальный код bot handlers;
- доступ бота к защищённому backend;
- работоспособную схему профиля и sleep check-ins;
- запись и чтение данных;
- недельную агрегацию и детерминированную NBA.

## Что не доказано этими скриншотами

- фактическая контейнерная топология и restart policy;
- PostgreSQL вместо SQLite;
- backup/restore;
- сохранение после полного перезапуска VM;
- мониторинг и длительный uptime.

## Последующая эксплуатационная проверка

Отдельный отчёт оператора deployment host подтвердил:

- `docker compose down` без `-v` и последующий `up -d`;
- сохранение volume `healthos-agent_pgdata`;
- healthy-состояние PostgreSQL и backend, работающий bot polling;
- `/health/live=ok`, `/health/ready=ready`, Alembic `20260710_0002`;
- отсутствие ошибок и Telegram polling-конфликтов `409`;
- сохранение baseline `/sleep/weekly`: `1/7`, `7.5 ч`, качество `4`, энергия `3`;
- восстановление backup в отдельной временной PostgreSQL-среде.

Таким образом, пункты про контейнеры, PostgreSQL, persistence и restore закрыты
последующей проверкой. Длительный uptime и внешний alerting всё ещё не доказаны.
