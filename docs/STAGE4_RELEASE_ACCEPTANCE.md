# HealthOS Stage 4 — release acceptance

Дата приёмки: 10 июля 2026 года.

## Проверенный контур

- реальный Telegram Bot API и polling;
- bot → защищённый FastAPI backend → PostgreSQL;
- профиль, утренний sleep check-in, недельная агрегация и одна NBA;
- PostgreSQL schema revision `20260710_0002`;
- полный `docker compose down` без удаления volume и последующий `up -d`;
- сохранение пользовательских данных после перезапуска;
- backup и restore в отдельной временной PostgreSQL-среде;
- отсутствие ошибок и polling-конфликтов `409` во время приёмки.

Контрольный baseline после restart и restore: `1/7`, `7.5 ч`, качество `4`,
энергия `3`; профиль: `Asia/Yekaterinburg`, цель сна `480` минут.

## Артефакты исходного RC

- deployed commit: `9a76f2250785d61640950c8f43da41b33f0420d5`;
- backup: `healthos-db-backup-stage4-20260710-170030.sql`;
- backup SHA-256: `a5a07a536060394a5e14900022071338ef228e2d3036b309b8ed0acf0cce3cde`;
- входной bundle SHA-256:
  `616b10f18e7c4db4c7184aa3fd62c411326e911bd85fc2cfa21d26c029fb7f6b`.

## Граница доказательств

Codex независимо проверил bundle, историю, diff, отсутствие типовых секретов и
локальный тестовый набор. Финальные прямые зависимости зафиксированы на версиях,
с которыми прошли 26/26 тестов. Docker/restart/restore результаты получены из отчёта
оператора deployment host; прямого доступа Codex к этому серверу не было.

После аудита RC в текущую ветку добавлены исправления пакетного импорта bot
transport, обработки aiohttp-ошибок/файлов и loopback bind при host networking.
Текущий HEAD должен пройти короткий deployment smoke и GitHub CI перед merge.
