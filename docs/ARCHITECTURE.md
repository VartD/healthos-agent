# Архитектура HealthOS

## Фактическая архитектура

В отличие от заявленного в описании проекта стека (React Native, Aiogram, FSM, 14 AI-агентов, GPT-4.1-mini, APScheduler, Redis), **фактический код** в репозитории представляет собой значительно более простую систему — MVP-монолит без внешних AI-вызовов и без асинхронных очередей.

### Компоненты и связи
1. **Telegram Bot (`bot/telegram_bot.py`)**
   - Написан на `python-telegram-bot` v21+ (не Aiogram).
   - Работает в режиме polling (не webhook).
   - Не использует FSM (Finite State Machine).
   - Каждая команда (например, `/water`, `/glucose`) асинхронно вызывает Backend API,
     передаёт сервисный `X-API-Key`, а затем возвращает пользователю текстовый ответ.
2. **Backend API (`backend/app/main.py`)**
   - Написан на FastAPI (синхронные маршруты, без async/await).
   - Содержит всего **3 API-операции** (а не заявленные 15):
     - `POST /events` — создание события.
     - `GET /events` — получение списка событий.
     - `GET /analyze` — анализ пользователя (возвращает режим, риски, команды).
   - Не использует LLM или AI-агентов. Вся логика зашита в детерминированные python-функции (движки).
   - Операции с health-data закрыты сервисным API-key. Полноценной пользовательской
     авторизации пока нет.
3. **Engines (Движки)**
   - `state_engine.py`: вычисляет режим (NORMAL, TRAINING, STABILIZATION и т.д.) на основе порогов (например, глюкоза > 7).
   - `risk_engine.py`: вычисляет коды рисков (например, `coffee_low_water`) по жестким if/else правилам.
   - `command_engine.py` и `prediction_engine.py`: генерируют текстовые рекомендации и прогнозы на основе словарей (маппинг режимов и рисков на строки).
4. **База данных**
   - PostgreSQL (через psycopg2 и SQLAlchemy ORM).
   - Единственная таблица: `health_events` (а не заявленные 9 ORM-моделей).

### Стек и точные версии
- **Python**: 3.11 (в Dockerfile) / 3.12.3 (локально)
- **FastAPI**: 0.136.1
- **Uvicorn**: 0.47.0
- **SQLAlchemy**: 2.0.51
- **Pydantic**: 2.13.4
- **psycopg2-binary**: 2.9.12
- **python-telegram-bot**: >=21.0
- **Docker**: `postgres:16-alpine`, `python:3.11-slim`

### Точки входа
- **Bot**: `python telegram_bot.py`
- **Backend**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Чего НЕТ в коде (хотя заявлено)
- **Aiogram**: Отсутствует.
- **Redis или очереди**: Отсутствует.
- **APScheduler**: Отсутствует (нет cron-задач).
- **Telegram Mini App**: Отсутствует (нет frontend-кода, HTML/JS/TS).
- **React Native / Expo**: Отсутствует (мобильного приложения нет).
- **AI-модели и провайдеры**: Отсутствует (нет OpenAI/GPT вызовов, нет langchain).
- **Cloudflare Tunnel / Tor**: В коде есть только удаление proxy-переменных окружения для бота (`os.environ.pop`), самого туннеля в репозитории нет.
- **Digital Twin / Longevity Intelligence**: Отсутствует.
- **Vision-анализ (Apple Watch)**: Отсутствует (нет загрузки фото).
- **15 API endpoints**: Отсутствуют (реализовано только 3).
- **9 ORM-моделей**: Отсутствуют (реализована только 1).

## Mermaid Диаграмма фактической архитектуры

```mermaid
flowchart TD
    User([Пользователь Telegram])
    Bot[Telegram Bot\npython-telegram-bot]
    API[FastAPI Backend\nпорт 8000]
    DB[(PostgreSQL\nhealthos)]
    
    User -->|/water 500| Bot
    Bot -->|POST /events| API
    API -->|INSERT| DB
    Bot -->|GET /analyze| API
    API -->|SELECT| DB
    API -->|Risk Engine| API
    API -->|State Engine| API
    API -->|JSON Digest| Bot
    Bot -->|Текстовый ответ| User
```

## База Данных

- **ORM-модели**: `HealthEvent`
- **Схема**:
  - `id`: Integer, PK
  - `user_id`: String(128), Index
  - `timestamp`: DateTime(timezone=True)
  - `event_type`: Enum (water, glucose, uric_acid, blood_pressure, food, coffee, tea, supplement, medication, workout, sauna, sleep, symptom)
  - `value`: Float, nullable
  - `unit`: String(64), nullable
  - `note`: Text, nullable
  - `event_metadata`: JSON, nullable
- **Миграции**: Отсутствуют (Alembic не используется, таблицы создаются через `Base.metadata.create_all`).
- **Persistent Volume**: Используется в `docker-compose.yml` (`pgdata:/var/lib/postgresql/data`).

## Инфраструктура и Деплой
- **Docker Compose**: Есть файл `docker-compose.yml`, который описывает `postgres` и `backend`. Бот туда не включен. Запуск через Docker не проверялся локально из-за ограничений песочницы.
- **Tor/Cloudflare**: Инфраструктурные скрипты отсутствуют.
- **CI/CD**: Отсутствует.
- **Мониторинг/логи**: Только стандартный `logging` в stdout.
