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
