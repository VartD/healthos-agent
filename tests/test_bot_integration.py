import asyncio
from dataclasses import dataclass, field

import httpx

from app.main import app
from bot import telegram_bot


@dataclass
class FakeChat:
    id: int = 123456


@dataclass
class FakeMessage:
    text: str = ""
    replies: list[str] = field(default_factory=list)

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@dataclass
class FakeUpdate:
    effective_chat: FakeChat = field(default_factory=FakeChat)
    message: FakeMessage = field(default_factory=FakeMessage)


@dataclass
class FakeContext:
    args: list[str]
    user_data: dict = field(default_factory=dict)


def route_bot_http_to_backend(monkeypatch) -> None:
    real_async_client = httpx.AsyncClient

    def asgi_client(**_kwargs):
        return real_async_client(
            transport=httpx.ASGITransport(app=app),
            base_url="http://healthos.test",
        )

    monkeypatch.setattr(telegram_bot.httpx, "AsyncClient", asgi_client)


def test_profile_morning_weekly_and_status_commands_use_real_backend(
    client, monkeypatch
):
    route_bot_http_to_backend(monkeypatch)
    update = FakeUpdate()

    async def scenario() -> None:
        await telegram_bot.cmd_profile(
            update, FakeContext(args=["8", "Asia/Yekaterinburg"])
        )
        await telegram_bot.cmd_morning(
            update,
            FakeContext(args=["7.5", "4", "1", "3", "спал", "спокойно"]),
        )
        await telegram_bot.cmd_sleepweek(update, FakeContext(args=[]))
        await telegram_bot.cmd_status(update, FakeContext(args=[]))

    asyncio.run(scenario())

    assert len(update.message.replies) == 4
    assert update.message.replies[0].startswith("Профиль сохранён")
    assert "Утренний чекин сохранён" in update.message.replies[1]
    assert "NEXT BEST ACTION" in update.message.replies[1]
    assert "СОН ЗА 7 ДНЕЙ" in update.message.replies[2]
    assert "Заполнено: 1/7" in update.message.replies[2]
    assert "РЕЖИМ:" in update.message.replies[3]


def test_morning_command_rejects_invalid_local_input_without_backend(client):
    update = FakeUpdate()
    asyncio.run(
        telegram_bot.cmd_morning(
            update,
            FakeContext(args=["не-число", "4", "1", "3"]),
        )
    )
    assert update.message.replies == ["Проверьте числовые значения чекина."]


def test_free_text_event_is_saved_and_acknowledged_concisely(client, monkeypatch):
    route_bot_http_to_backend(monkeypatch)
    update = FakeUpdate(message=FakeMessage(text="Выпил 300 мл воды"))

    asyncio.run(telegram_bot.handle_free_text(update, FakeContext(args=[])))

    assert update.message.replies[0].startswith("Записал ✅ Вода: 300 мл.")
    response = client.get(
        "/events",
        params={"user_id": str(update.effective_chat.id)},
        headers={"X-API-Key": "test-healthos-api-key-that-is-long-enough"},
    )
    assert response.status_code == 200
    assert response.json()[0]["event_type"] == "water"


def test_ambiguous_free_text_is_not_saved(client, monkeypatch):
    route_bot_http_to_backend(monkeypatch)
    update = FakeUpdate(message=FakeMessage(text="Сегодня обычный день"))

    asyncio.run(telegram_bot.handle_free_text(update, FakeContext(args=[])))

    assert "ничего не записал" in update.message.replies[0]
    response = client.get(
        "/events",
        params={"user_id": str(update.effective_chat.id)},
        headers={"X-API-Key": "test-healthos-api-key-that-is-long-enough"},
    )
    assert response.json() == []


def test_uncertain_volume_requires_confirmation_before_saving(client, monkeypatch):
    route_bot_http_to_backend(monkeypatch)
    context = FakeContext(args=[])
    update = FakeUpdate(message=FakeMessage(text="Вода 300"))

    asyncio.run(telegram_bot.handle_free_text(update, context))
    assert "Ответьте «да» или «нет»" in update.message.replies[0]
    assert "pending_event" in context.user_data

    update.message.text = "да"
    asyncio.run(telegram_bot.handle_free_text(update, context))
    assert update.message.replies[1].startswith("Записал ✅ Вода: 300 мл.")
    assert "pending_event" not in context.user_data

    response = client.get(
        "/events",
        params={"user_id": str(update.effective_chat.id)},
        headers={"X-API-Key": "test-healthos-api-key-that-is-long-enough"},
    )
    assert len(response.json()) == 1


def test_uncertain_volume_can_be_cancelled_without_saving(client, monkeypatch):
    route_bot_http_to_backend(monkeypatch)
    context = FakeContext(args=[])
    update = FakeUpdate(message=FakeMessage(text="Кофе 200"))

    asyncio.run(telegram_bot.handle_free_text(update, context))
    update.message.text = "нет"
    asyncio.run(telegram_bot.handle_free_text(update, context))

    assert update.message.replies[-1] == "Отменил. Ничего не записано."
    response = client.get(
        "/events",
        params={"user_id": str(update.effective_chat.id)},
        headers={"X-API-Key": "test-healthos-api-key-that-is-long-enough"},
    )
    assert response.json() == []


def test_expired_confirmation_is_never_saved(client, monkeypatch):
    route_bot_http_to_backend(monkeypatch)
    context = FakeContext(
        args=[],
        user_data={
            "pending_event": {
                "payload": {"event_type": "water", "value": 300, "unit": "ml"},
                "acknowledgement": "Вода: 300 мл",
                "created_at": 0,
            }
        },
    )
    update = FakeUpdate(message=FakeMessage(text="да"))

    asyncio.run(telegram_bot.handle_free_text(update, context))

    assert "ничего не записал" in update.message.replies[0]
    response = client.get(
        "/events",
        params={"user_id": str(update.effective_chat.id)},
        headers={"X-API-Key": "test-healthos-api-key-that-is-long-enough"},
    )
    assert response.json() == []


def test_natural_sleep_checkin_uses_existing_sleep_backend(client, monkeypatch):
    route_bot_http_to_backend(monkeypatch)
    update = FakeUpdate(
        message=FakeMessage(
            text="Спал 7,5 часов, качество 4, просыпался 1 раз, энергия 3"
        )
    )

    asyncio.run(telegram_bot.handle_free_text(update, FakeContext(args=[])))

    assert update.message.replies[0].startswith("Записал ✅ Сон 7.5 ч")
    weekly = client.get(
        "/sleep/weekly",
        params={"user_id": str(update.effective_chat.id)},
        headers={"X-API-Key": "test-healthos-api-key-that-is-long-enough"},
    )
    assert weekly.json()["days_logged"] == 1


def test_incomplete_natural_sleep_checkin_is_not_saved(client, monkeypatch):
    route_bot_http_to_backend(monkeypatch)
    update = FakeUpdate(message=FakeMessage(text="Спал сегодня 7 часов"))

    asyncio.run(telegram_bot.handle_free_text(update, FakeContext(args=[])))

    assert "нужны четыре значения" in update.message.replies[0]
    events = client.get(
        "/events",
        params={"user_id": str(update.effective_chat.id)},
        headers={"X-API-Key": "test-healthos-api-key-that-is-long-enough"},
    )
    assert events.json() == []
