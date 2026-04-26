from __future__ import annotations

import logging
from typing import Awaitable, Callable

from nio import AsyncClient, LoginResponse, RoomMessageText

logger = logging.getLogger(__name__)
MessageCallback = Callable[[str, str, str], Awaitable[None]]


def _preview_text(text: str, limit: int = 160) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit - 3]}..."


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
        response = await self._client.login(self._password)
        if isinstance(response, LoginResponse):
            logger.info("Matrix login succeeded for %s", self._user)
            return True
        logger.error("Matrix login failed for %s: %s", self._user, response)
        await self._client.close()
        return False

    async def _join_rooms(self) -> None:
        for room_id in self._rooms:
            await self._client.join(room_id)

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
            await self._callback(room.room_id, event.sender, event.body)

    async def send_text(self, room_id: str, text: str) -> None:
        logger.info("Sending Matrix text event to %s: %s", room_id, _preview_text(text))
        await self._client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": text},
        )

    async def set_typing(
        self, room_id: str, typing: bool, timeout: int = 30000
    ) -> None:
        try:
            await self._client.room_typing(room_id, typing, timeout=timeout)
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
