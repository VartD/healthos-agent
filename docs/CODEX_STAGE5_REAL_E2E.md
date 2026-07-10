# Codex Stage 5 — real Telegram E2E

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
