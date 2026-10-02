"""Voice-session routes backed by the media service."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_csrf
from app.api.errors import ApiError
from app.api.schemas import MediaSessionRequest, RealtimeEvent, VoiceSessionResponse
from app.api.websocket.manager import realtime_manager
from app.application.media_client import MediaServiceClient, MediaServiceError
from app.application.policies import require_member
from app.application.voice_registry import ActiveVoiceSession, voice_registry
from app.config import settings
from app.infrastructure.auth.sessions import AuthContext
from app.infrastructure.database.models import Community, VoiceChannel
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["voice"])
media_client = MediaServiceClient()


@router.post("/channels/{channel_id}/voice-session", response_model=VoiceSessionResponse)
async def create_voice_session(
    channel_id: UUID,
    context: AuthContext = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> VoiceSessionResponse:
    result = await db.execute(
        select(VoiceChannel, Community)
        .join(Community, Community.id == VoiceChannel.community_id)
        .where(VoiceChannel.id == channel_id)
    )
    row = result.one_or_none()
    if row is None:
        raise ApiError(404, "channel_not_found", "Voice channel not found")
    channel, community = row
    await require_member(db, community.id, context.user.id)

    existing = voice_registry.get_for_user(context.user.id)
    if existing is not None:
        raise ApiError(409, "already_in_voice_channel", "User already has an active voice session")

    request = MediaSessionRequest(
        user_id=context.user.id,
        community_id=community.id,
        channel_id=channel.id,
        display_name=context.user.display_name,
        max_participants=settings.max_participants_per_voice_channel,
        idempotency_key=str(uuid4()),
    )
    try:
        media_session = await media_client.create_voice_session(request)
    except MediaServiceError as exc:
        raise ApiError(exc.status_code, exc.code, exc.message) from exc

    voice_registry.add(
        ActiveVoiceSession(
            session_id=media_session.session_id,
            user_id=context.user.id,
            community_id=community.id,
            channel_id=channel.id,
        )
    )
    return VoiceSessionResponse(**media_session.model_dump())


@router.delete("/voice-sessions/{session_id}", status_code=204)
async def delete_voice_session(
    session_id: str,
    response: Response,
    context: AuthContext = Depends(require_csrf),
) -> Response:
    active = voice_registry.get(session_id)
    if active is None:
        raise ApiError(404, "voice_session_not_found", "Voice session not found")
    if active.user_id != context.user.id:
        raise ApiError(
            403,
            "voice_session_owner_required",
            "Voice session owner permission is required",
        )

    try:
        await media_client.delete_voice_session(session_id)
    except MediaServiceError as exc:
        raise ApiError(exc.status_code, exc.code, exc.message) from exc

    voice_registry.remove(session_id)
    await realtime_manager.broadcast(
        RealtimeEvent(
            type="participant.left",
            event_id=str(uuid4()),
            occurred_at=datetime.now(UTC),
            community_id=active.community_id,
            channel_id=active.channel_id,
            payload={"user_id": str(active.user_id), "session_id": session_id},
        )
    )
    response.status_code = 204
    return response
