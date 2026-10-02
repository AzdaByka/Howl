"""Private media-service callbacks."""

import hmac

from fastapi import APIRouter, Header

from app.api.errors import ApiError
from app.api.schemas import MediaEventRequest, RealtimeEvent
from app.api.websocket.manager import realtime_manager
from app.application.voice_registry import voice_registry
from app.config import settings

router = APIRouter(prefix="/internal/v1", tags=["internal"])


def require_media_token(token: str | None) -> None:
    expected = settings.media_internal_token.get_secret_value()
    if not token or not hmac.compare_digest(token, expected):
        raise ApiError(401, "internal_auth_failed", "Internal authentication failed")


@router.post("/events", status_code=202)
async def receive_media_event(
    payload: MediaEventRequest,
    x_internal_token: str | None = Header(default=None),
) -> dict[str, str]:
    require_media_token(x_internal_token)
    if payload.session_id and payload.type in {"participant.left", "voice_session.ended"}:
        voice_registry.remove(payload.session_id)

    accepted = await realtime_manager.broadcast(
        RealtimeEvent(
            type=payload.type,
            event_id=payload.event_id,
            occurred_at=payload.occurred_at,
            community_id=payload.community_id,
            channel_id=payload.channel_id,
            payload={
                **payload.payload,
                "user_id": str(payload.user_id) if payload.user_id else None,
            },
        )
    )
    return {"status": "accepted" if accepted else "duplicate"}
