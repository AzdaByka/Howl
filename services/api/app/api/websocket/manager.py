"""In-memory realtime connection manager for a single API instance."""

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import WebSocket

from app.api.schemas import RealtimeEvent


@dataclass(slots=True)
class RealtimeConnection:
    websocket: WebSocket
    user_id: UUID
    subscriptions: set[tuple[UUID, UUID | None]] = field(default_factory=set)


class RealtimeManager:
    def __init__(self) -> None:
        self._connections: list[RealtimeConnection] = []
        self._seen_event_ids: set[str] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID) -> RealtimeConnection:
        await websocket.accept()
        connection = RealtimeConnection(websocket=websocket, user_id=user_id)
        async with self._lock:
            self._connections.append(connection)
        return connection

    async def disconnect(self, connection: RealtimeConnection) -> None:
        async with self._lock:
            if connection in self._connections:
                self._connections.remove(connection)

    async def broadcast(self, event: RealtimeEvent) -> bool:
        async with self._lock:
            if event.event_id in self._seen_event_ids:
                return False
            self._seen_event_ids.add(event.event_id)
            connections = list(self._connections)

        recipients: list[RealtimeConnection] = []
        for connection in connections:
            if event.community_id is None:
                recipients.append(connection)
                continue
            if any(
                community_id == event.community_id
                and (channel_id is None or channel_id == event.channel_id)
                for community_id, channel_id in connection.subscriptions
            ):
                recipients.append(connection)

        for connection in recipients:
            try:
                await connection.websocket.send_json(event.model_dump(mode="json"))
            except Exception:
                await self.disconnect(connection)
        return True


realtime_manager = RealtimeManager()
