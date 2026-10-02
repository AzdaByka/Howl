"""Authorization policies shared by API routes."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.infrastructure.database.models import Community, CommunityMember


async def get_community(db: AsyncSession, community_id: UUID) -> Community:
    community = await db.get(Community, community_id)
    if community is None:
        raise ApiError(404, "community_not_found", "Community not found")
    return community


async def require_member(db: AsyncSession, community_id: UUID, user_id: UUID) -> Community:
    community = await get_community(db, community_id)
    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise ApiError(403, "community_membership_required", "Community membership is required")
    return community


async def require_owner(db: AsyncSession, community_id: UUID, user_id: UUID) -> Community:
    community = await get_community(db, community_id)
    if community.owner_id != user_id:
        raise ApiError(403, "community_owner_required", "Community owner permission is required")
    return community
