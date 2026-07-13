FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_bot.py .
COPY aiohttp_request.py .
COPY natural_language.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "telegram_bot.py"]
