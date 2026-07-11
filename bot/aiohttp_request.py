"""Custom python-telegram-bot request adapter backed by aiohttp."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from telegram.error import NetworkError, TimedOut
from telegram.request import BaseRequest, RequestData


class AiohttpRequest(BaseRequest):
    """PTB BaseRequest implementation backed by aiohttp."""

    @property
    def read_timeout(self) -> float | None:
        return self._read_timeout

    @property
    def write_timeout(self) -> float | None:
        return self._write_timeout

    @property
    def connect_timeout(self) -> float | None:
        return self._connect_timeout

    @property
    def pool_timeout(self) -> float | None:
        return self._pool_timeout

    def __init__(
        self,
        read_timeout: float = 30.0,
        write_timeout: float = 30.0,
        connect_timeout: float = 10.0,
        pool_timeout: float = 10.0,
    ) -> None:
        self._read_timeout = read_timeout
        self._write_timeout = write_timeout
        self._connect_timeout = connect_timeout
        self._pool_timeout = pool_timeout
        self._session: aiohttp.ClientSession | None = None

    async def initialize(self) -> None:
        if self._session is not None and not self._session.closed:
            return
        connector = aiohttp.TCPConnector(limit=10)
        self._session = aiohttp.ClientSession(connector=connector, trust_env=False)

    async def shutdown(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    @staticmethod
    def _timeout_value(value: Any, default: float | None) -> float | None:
        """Resolve PTB's DEFAULT_NONE sentinel without importing private APIs."""
        return default if value is BaseRequest.DEFAULT_NONE else value

    @staticmethod
    def _request_body(request_data: RequestData | None) -> Any:
        if request_data is None:
            return None

        fields = request_data.json_parameters
        files = request_data.multipart_data
        if not files:
            return fields or None

        form = aiohttp.FormData()
        for name, value in fields.items():
            form.add_field(name, value)
        for name, (filename, content, content_type) in files.items():
            form.add_field(
                name,
                content,
                filename=filename,
                content_type=content_type,
            )
        return form

    async def do_request(
        self,
        url: str,
        method: str,
        request_data: RequestData | None = None,
        read_timeout: Any = BaseRequest.DEFAULT_NONE,
        write_timeout: Any = BaseRequest.DEFAULT_NONE,
        connect_timeout: Any = BaseRequest.DEFAULT_NONE,
        pool_timeout: Any = BaseRequest.DEFAULT_NONE,
    ) -> tuple[int, bytes]:
        if self._session is None or self._session.closed:
            await self.initialize()

        effective_read = self._timeout_value(read_timeout, self._read_timeout)
        effective_connect = self._timeout_value(
            connect_timeout, self._connect_timeout
        )
        timeout = aiohttp.ClientTimeout(
            total=None,
            connect=effective_connect,
            sock_connect=effective_connect,
            sock_read=effective_read,
        )
        body = self._request_body(request_data)

        try:
            assert self._session is not None
            async with self._session.request(
                method,
                url,
                data=body,
                headers={"User-Agent": self.USER_AGENT},
                timeout=timeout,
            ) as resp:
                return resp.status, await resp.read()
        except asyncio.TimeoutError as exc:
            raise TimedOut from exc
        except aiohttp.ClientError as exc:
            raise NetworkError(
                f"aiohttp.{exc.__class__.__name__}: {exc}"
            ) from exc
