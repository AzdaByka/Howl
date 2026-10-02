"""Voice channel routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_auth, require_csrf
from app.api.schemas import ChannelCreateRequest, ChannelResponse
from app.application.policies import require_member, require_owner
from app.infrastructure.auth.sessions import AuthContext
from app.infrastructure.database.models import VoiceChannel
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["channels"])


@router.get("/communities/{community_id}/channels", response_model=list[ChannelResponse])
async def list_channels(
    community_id: UUID,
    context: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> list[VoiceChannel]:
    await require_member(db, community_id, context.user.id)
    result = await db.scalars(
        select(VoiceChannel)
        .where(VoiceChannel.community_id == community_id)
        .order_by(VoiceChannel.created_at)
    )
    return list(result.all())


@router.post(
    "/communities/{community_id}/channels",
    response_model=ChannelResponse,
    status_code=201,
)
async def create_channel(
    community_id: UUID,
    payload: ChannelCreateRequest,
    context: AuthContext = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> VoiceChannel:
    await require_owner(db, community_id, context.user.id)
    channel = VoiceChannel(community_id=community_id, name=payload.name.strip())
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel
