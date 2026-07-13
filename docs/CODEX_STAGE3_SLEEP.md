# Codex Stage 3 — модуль сна

Дата: 10 июля 2026

## Цель

Создать первый законченный пользовательский контур HealthOS без LLM и без
медицинских назначений: измерение → недельный синтез → одна проверяемая NBA.

## Реализовано

- `user_profiles`: IANA timezone, персональная цель сна, поля будущих reminders.
- `sleep_checkins`: дата, длительность, качество, пробуждения, энергия, заметка.
- Связь sleep check-in с `health_events` один-к-одному.
- Upsert по `(user_id, sleep_date)` без дублей.
- API профиля, чекина, истории и недельной сводки.
- Детерминированный выбор одной NBA.
- Telegram-команды `/profile`, `/morning`, `/sleepweek`.
- Alembic revision `20260710_0002` и DB-level check constraints.

## Проверено

- 21/21 тест.
- Upgrade `0001 → 0002` на SQLite.
- Alembic schema check без расхождений.
- Offline PostgreSQL DDL для revision `0002`.
- API smoke: profile → sleep check-in → weekly summary на мигрированной БД.

## Ограничения

- Нет автоматических reminders и вечернего чекина.
- Telegram polling не проверен с реальным token.
- Нет клинической интерпретации сна.
- NBA основана на персональной цели и поведенческом эксперименте, а не на диагнозе.
