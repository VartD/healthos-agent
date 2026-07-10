# Codex Stage 4 — Telegram verification

Дата: 10 июля 2026

## Реализовано

- Integration-тест handlers `/profile`, `/morning`, `/sleepweek`, `/status`.
- Настоящий FastAPI, ORM и тестовая БД; подменяется только Telegram transport.
- Проверка локальной ошибки команды `/morning`.
- Безопасный `scripts/smoke_real_services.py` для реального окружения.

## Real smoke проверяет

- backend liveness/readiness;
- сервисную авторизацию;
- Telegram `getMe`;
- отсутствие webhook для polling;
- опциональную отправку одного сообщения только с `--send-message`.

## Результат текущей среды

- 23/23 автоматизированных теста проходят.
- Real smoke корректно завершился кодом 2: `TELEGRAM_BOT_TOKEN` отсутствует.
- Docker, `HEALTHOS_API_KEY` и `gh` также отсутствуют.

Это блокер среды и секретов, а не подтверждённый дефект кода бота.
