"""Authenticated realtime WebSocket endpoint."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.schemas import RealtimeSubscribe
from app.api.websocket.manager import RealtimeConnection, realtime_manager
from app.config import settings
from app.infrastructure.auth.sessions import get_auth_context
from app.infrastructure.database.models import CommunityMember, VoiceChannel
from app.infrastructure.database.session import SessionLocal

router = APIRouter(tags=["realtime"])


async def _can_subscribe(connection: RealtimeConnection, command: RealtimeSubscribe) -> bool:
    async with SessionLocal() as db:
        membership = await db.scalar(
            select(CommunityMember).where(
                CommunityMember.community_id == command.community_id,
                CommunityMember.user_id == connection.user_id,
            )
        )
        if membership is None:
            return False
        if command.channel_id is None:
            return True
        channel = await db.scalar(
            select(VoiceChannel).where(
                VoiceChannel.id == command.channel_id,
                VoiceChannel.community_id == command.community_id,
            )
        )
        return channel is not None


@router.websocket("/realtime")
async def realtime(websocket: WebSocket) -> None:
    async with SessionLocal() as db:
        context = await get_auth_context(db, websocket.cookies.get(settings.session_cookie_name))
    if context is None:
        await websocket.close(code=1008, reason="Authentication required")
        return

    connection = await realtime_manager.connect(websocket, context.user.id)
    try:
        while True:
            raw = await websocket.receive_json()
            message_type = raw.get("type")
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if message_type != "subscribe":
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "unsupported_message",
                        "message": "Unsupported message type",
                    }
                )
                continue

            try:
                command = RealtimeSubscribe.model_validate(raw)
            except ValueError as exc:
                await websocket.send_json(
                    {"type": "error", "code": "invalid_subscription", "message": str(exc)}
                )
                continue

            if not await _can_subscribe(connection, command):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "subscription_forbidden",
                        "message": "Subscription is not allowed",
                    }
                )
                continue

            connection.subscriptions.add((command.community_id, command.channel_id))
            await websocket.send_json(
                {
                    "type": "subscribed",
                    "community_id": str(command.community_id),
                    "channel_id": str(command.channel_id) if command.channel_id else None,
                }
            )
    except WebSocketDisconnect:
        pass
    finally:
        await realtime_manager.disconnect(connection)
