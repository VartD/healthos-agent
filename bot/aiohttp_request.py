"""Custom PTB request adapter using aiohttp instead of httpx.

In the Manus sandbox, httpx's TLS handshake hangs when connecting to
api.telegram.org, while aiohttp works fine. This module provides a
drop-in replacement for HTTPXRequest.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Optional, Tuple

import aiohttp
from telegram.request import BaseRequest
from telegram.request._requestdata import RequestData


class AiohttpRequest(BaseRequest):
    """PTB BaseRequest implementation backed by aiohttp."""

    # PTB requires these abstract properties
    @property
    def read_timeout(self) -> Optional[float]:
        return self._read_timeout

    @property
    def write_timeout(self) -> Optional[float]:
        return self._write_timeout

    @property
    def connect_timeout(self) -> Optional[float]:
        return self._connect_timeout

    @property
    def pool_timeout(self) -> Optional[float]:
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
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        connector = aiohttp.TCPConnector(limit=10)
        self._session = aiohttp.ClientSession(connector=connector)

    async def shutdown(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def do_request(
        self,
        url: str,
        method: str,
        request_data: Optional[RequestData] = None,
        read_timeout: Optional[float] = None,
        write_timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        pool_timeout: Optional[float] = None,
    ) -> Tuple[int, bytes]:
        if self._session is None or self._session.closed:
            await self.initialize()

        total = read_timeout or self._read_timeout
        timeout = aiohttp.ClientTimeout(total=total)

        if request_data is None or not request_data.parameters:
            async with self._session.request(
                method, url, timeout=timeout
            ) as resp:
                return resp.status, await resp.read()

        # Build multipart form data (PTB always uses form encoding)
        form = aiohttp.FormData()
        for key, val in request_data.parameters.items():
            if hasattr(val, "read"):
                # File-like object
                form.add_field(key, val)
            elif isinstance(val, (dict, list)):
                form.add_field(key, json.dumps(val))
            else:
                form.add_field(key, str(val))

        async with self._session.request(
            method, url, data=form, timeout=timeout
        ) as resp:
            return resp.status, await resp.read()
