import asyncio
from types import SimpleNamespace

import aiohttp
import pytest
from telegram.error import NetworkError

from bot.aiohttp_request import AiohttpRequest


class FakeResponse:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def read(self) -> bytes:
        return b'{"ok": true}'


class FakeSession:
    closed = False

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse()


def test_adapter_sends_json_parameters_and_resolves_default_timeouts():
    adapter = AiohttpRequest(read_timeout=35.0, connect_timeout=7.0)
    session = FakeSession()
    adapter._session = session
    request_data = SimpleNamespace(
        json_parameters={"chat_id": "123", "text": "ok"},
        multipart_data={},
    )

    status, body = asyncio.run(
        adapter.do_request("https://api.telegram.org/test", "POST", request_data)
    )

    assert (status, body) == (200, b'{"ok": true}')
    call = session.calls[0]
    assert call["data"] == {"chat_id": "123", "text": "ok"}
    assert call["timeout"].sock_read == 35.0
    assert call["timeout"].connect == 7.0


def test_adapter_builds_multipart_body_for_files():
    adapter = AiohttpRequest()
    session = FakeSession()
    adapter._session = session
    request_data = SimpleNamespace(
        json_parameters={"chat_id": "123", "photo": "attach://file_0"},
        multipart_data={"file_0": ("image.jpg", b"image", "image/jpeg")},
    )

    asyncio.run(
        adapter.do_request("https://api.telegram.org/test", "POST", request_data)
    )

    assert isinstance(session.calls[0]["data"], aiohttp.FormData)


def test_adapter_maps_aiohttp_errors_to_telegram_network_error():
    class BrokenSession:
        closed = False

        def request(self, method, url, **kwargs):
            raise aiohttp.ClientConnectionError("connection failed")

    adapter = AiohttpRequest()
    adapter._session = BrokenSession()

    with pytest.raises(NetworkError, match="ClientConnectionError"):
        asyncio.run(adapter.do_request("https://api.telegram.org/test", "POST"))
