# Инструкция по воспроизведению (Runbook)

Проект можно запустить локально без Docker (используя SQLite) или с помощью Docker Compose (PostgreSQL). Локальный вариант и автоматизированные тесты проверены Codex. Docker Compose описан в коде, но в текущей среде не проверялся.

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
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   API будет доступно по адресу `http://127.0.0.1:8000/docs`. База данных создастся автоматически при первом запуске.

4. **Запуск Telegram-бота**
   В новом терминале:
   ```bash
   cd bot
   python telegram_bot.py
   ```

## Вариант 2: Запуск через Docker Compose (Из кода, не проверялось локально из-за ограничений песочницы)

1. **Настройка окружения**
   Создайте файл `.env` с токеном бота (см. выше). База данных уже настроена в `docker-compose.yml`.

2. **Запуск**
   ```bash
   docker-compose up --build -d
   ```
   Это поднимет базу данных PostgreSQL и Backend API.

3. **Запуск бота**
   Бот не включен в `docker-compose.yml`. Его нужно запускать локально:
   ```bash
   cd bot
   python telegram_bot.py
   ```

## Автоматизированное тестирование

Из корня репозитория:

```bash
pytest
```

На этапе Codex P0 реализовано 13 тестов API, авторизации, фильтрации пользователей,
валидации и safety-логики. Telegram polling и Docker Compose пока требуют отдельной
интеграционной проверки.
