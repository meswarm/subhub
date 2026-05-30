from __future__ import annotations

import logging
from time import perf_counter
from typing import Awaitable, Callable

from nio import AsyncClient, LoginResponse, RoomMessageText

logger = logging.getLogger(__name__)
MessageCallback = Callable[[str, str, str], Awaitable[None]]


def _preview_text(text: str, limit: int = 160) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit - 3]}..."


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000


class MatrixTextClient:
    def __init__(
        self,
        homeserver: str,
        user: str,
        password: str,
        rooms: list[str],
        client: AsyncClient | None = None,
    ):
        self._client = client or AsyncClient(homeserver, user)
        self._homeserver = homeserver
        self._user = user
        self._password = password
        self._rooms = rooms
        self._callback: MessageCallback | None = None
        self._first_sync_done = False
        self._should_stop = False

    @staticmethod
    def event_types() -> tuple[str, ...]:
        return ("RoomMessageText",)

    def on_message(self, callback: MessageCallback) -> None:
        self._callback = callback

    async def login(self) -> bool:
        started_at = perf_counter()
        response = await self._client.login(self._password)
        if isinstance(response, LoginResponse):
            logger.info(
                "Matrix login succeeded for %s in %.1f ms",
                self._user,
                _elapsed_ms(started_at),
            )
            return True
        logger.error(
            "Matrix login failed for %s in %.1f ms: %s",
            self._user,
            _elapsed_ms(started_at),
            response,
        )
        await self._client.close()
        return False

    async def _join_rooms(self) -> None:
        for room_id in self._rooms:
            started_at = perf_counter()
            await self._client.join(room_id)
            logger.info(
                "Matrix join %s completed in %.1f ms",
                room_id,
                _elapsed_ms(started_at),
            )

    async def _on_room_message(self, room, event) -> None:
        if event.sender == self._client.user_id:
            return
        if not self._first_sync_done:
            return
        logger.info(
            "Received Matrix text event in %s from %s: %s",
            room.room_id,
            event.sender,
            _preview_text(event.body),
        )
        if self._callback:
            started_at = perf_counter()
            await self._callback(room.room_id, event.sender, event.body)
            logger.info(
                "Matrix text event callback completed for %s in %.1f ms",
                room.room_id,
                _elapsed_ms(started_at),
            )

    async def send_text(self, room_id: str, text: str) -> None:
        logger.info("Sending Matrix text event to %s: %s", room_id, _preview_text(text))
        started_at = perf_counter()
        await self._client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": text},
        )
        logger.info(
            "Matrix room_send completed for %s in %.1f ms",
            room_id,
            _elapsed_ms(started_at),
        )

    async def set_typing(
        self, room_id: str, typing: bool, timeout: int = 30000
    ) -> None:
        try:
            started_at = perf_counter()
            await self._client.room_typing(room_id, typing, timeout=timeout)
            logger.info(
                "Matrix room_typing=%s completed for %s in %.1f ms",
                typing,
                room_id,
                _elapsed_ms(started_at),
            )
        except Exception:
            logger.debug("Matrix typing update failed", exc_info=True)

    async def start_sync(self) -> None:
        self._client.add_event_callback(self._on_room_message, RoomMessageText)
        await self._join_rooms()
        await self._client.sync(timeout=10000)
        self._first_sync_done = True
        while not self._should_stop:
            await self._client.sync(timeout=5000)

    async def stop(self) -> None:
        self._should_stop = True
        await self._client.close()

    @property
    def rooms(self) -> list[str]:
        return self._rooms
