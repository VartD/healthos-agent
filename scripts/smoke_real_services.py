#!/usr/bin/env python3
"""Non-destructive preflight for a running HealthOS backend and Telegram bot.

Secrets are never printed. By default the script only calls read-only endpoints.
Use --send-message explicitly to send one smoke message to TELEGRAM_SMOKE_CHAT_ID.
"""

import argparse
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def fail(message: str, exit_code: int) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(exit_code)


def telegram_call(
    client: httpx.Client,
    token: str,
    method: str,
    payload: dict[str, str] | None = None,
) -> dict:
    try:
        response = client.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=payload or {},
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        fail(f"Telegram network error ({type(exc).__name__})", 4)
    try:
        data = response.json()
    except ValueError:
        fail(f"Telegram returned non-JSON status {response.status_code}", 4)
    if response.status_code != 200 or not data.get("ok"):
        description = str(data.get("description", "unknown Telegram error"))
        fail(f"Telegram rejected request: {description}", 4)
    return data["result"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--send-message",
        action="store_true",
        help="Send one test message to TELEGRAM_SMOKE_CHAT_ID.",
    )
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    api_key = os.getenv("HEALTHOS_API_KEY", "")
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    smoke_user_id = os.getenv("TELEGRAM_SMOKE_USER_ID", "smoke-preflight")

    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{20,}", token):
        fail("TELEGRAM_BOT_TOKEN is missing or has an invalid format", 2)
    if len(api_key) < 32:
        fail("HEALTHOS_API_KEY is missing or shorter than 32 characters", 2)

    with httpx.Client(trust_env=False) as client:
        for endpoint in ("/health/live", "/health/ready"):
            try:
                response = client.get(f"{backend_url}{endpoint}", timeout=10.0)
            except httpx.HTTPError as exc:
                fail(f"Backend network error at {endpoint} ({type(exc).__name__})", 3)
            if response.status_code != 200:
                fail(f"Backend {endpoint} returned {response.status_code}", 3)

        protected = client.get(
            f"{backend_url}/sleep/weekly",
            params={"user_id": smoke_user_id},
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )
        if protected.status_code != 200:
            fail(f"Protected backend API returned {protected.status_code}", 3)

        bot = telegram_call(client, token, "getMe")
        webhook = telegram_call(client, token, "getWebhookInfo")
        if webhook.get("url"):
            fail("A webhook is configured, but this HealthOS bot uses polling", 4)

        print(
            "OK: backend live/ready, protected API, Telegram getMe and polling mode"
        )
        print(f"Telegram bot username: @{bot.get('username', 'unknown')}")

        if args.send_message:
            chat_id = os.getenv("TELEGRAM_SMOKE_CHAT_ID", "")
            if not chat_id:
                fail("TELEGRAM_SMOKE_CHAT_ID is required with --send-message", 2)
            telegram_call(
                client,
                token,
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": "HealthOS smoke test: соединение с ботом работает.",
                },
            )
            print("OK: smoke message sent")


if __name__ == "__main__":
    main()
