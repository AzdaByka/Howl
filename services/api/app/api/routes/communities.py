"""Community and invitation routes."""

import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_auth, require_csrf
from app.api.errors import ApiError
from app.api.schemas import (
    CommunityCreateRequest,
    CommunityResponse,
    CommunitySummary,
    InvitePreviewResponse,
    InviteResponse,
)
from app.application.policies import require_member, require_owner
from app.config import settings
from app.infrastructure.auth.sessions import AuthContext
from app.infrastructure.auth.tokens import hash_token
from app.infrastructure.database.base import utc_now
from app.infrastructure.database.models import Community, CommunityMember, Invite
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["communities"])


@router.get("/me/communities", response_model=list[CommunitySummary])
async def list_my_communities(
    context: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> list[CommunitySummary]:
    member_count = (
        select(func.count(CommunityMember.user_id))
        .where(CommunityMember.community_id == Community.id)
        .correlate(Community)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Community, member_count.label("member_count"))
        .join(CommunityMember, CommunityMember.community_id == Community.id)
        .where(CommunityMember.user_id == context.user.id)
        .order_by(Community.created_at)
    )
    return [
        CommunitySummary(
            id=community.id,
            name=community.name,
            owner_id=community.owner_id,
            created_at=community.created_at,
            updated_at=community.updated_at,
            member_count=member_count,
        )
        for community, member_count in result.all()
    ]


@router.post("/communities", response_model=CommunityResponse, status_code=201)
async def create_community(
    payload: CommunityCreateRequest,
    context: AuthContext = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> Community:
    community = Community(owner_id=context.user.id, name=payload.name.strip())
    db.add(community)
    await db.flush()
    db.add(CommunityMember(community_id=community.id, user_id=context.user.id, joined_at=utc_now()))
    await db.commit()
    await db.refresh(community)
    return community


@router.get("/communities/{community_id}", response_model=CommunityResponse)
async def get_community_details(
    community_id: UUID,
    context: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> Community:
    return await require_member(db, community_id, context.user.id)


@router.post("/communities/{community_id}/leave", status_code=204)
async def leave_community(
    community_id: UUID,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> Response:
    community = await require_member(db, community_id, context.user.id)
    if community.owner_id == context.user.id:
        raise ApiError(409, "owner_cannot_leave", "Community owner cannot leave the community")
    await db.execute(
        delete(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == context.user.id,
        )
    )
    await db.commit()
    response.status_code = 204
    return response


@router.post("/communities/{community_id}/invites", response_model=InviteResponse, status_code=201)
async def create_invite(
    community_id: UUID,
    context: AuthContext = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> InviteResponse:
    await require_owner(db, community_id, context.user.id)
    raw_token = secrets.token_urlsafe(32)
    invite = Invite(
        community_id=community_id,
        created_by=context.user.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(days=settings.invite_ttl_days),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return InviteResponse(
        id=invite.id,
        community_id=invite.community_id,
        token=raw_token,
        expires_at=invite.expires_at,
    )


@router.get("/invites/{token}", response_model=InvitePreviewResponse)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)) -> InvitePreviewResponse:
    result = await db.execute(
        select(Invite, Community)
        .join(Community, Community.id == Invite.community_id)
        .where(Invite.token_hash == hash_token(token))
    )
    row = result.one_or_none()
    if row is None:
        raise ApiError(404, "invite_not_found", "Invite not found")
    invite, community = row
    expired = invite.revoked_at is not None or invite.expires_at <= utc_now()
    return InvitePreviewResponse(
        community_id=community.id,
        community_name=community.name,
        expires_at=invite.expires_at,
        is_expired=expired,
    )


@router.post("/invites/{token}/accept", response_model=CommunityResponse)
async def accept_invite(
    token: str,
    context: AuthContext = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> Community:
    invite = await db.scalar(select(Invite).where(Invite.token_hash == hash_token(token)))
    if invite is None:
        raise ApiError(404, "invite_not_found", "Invite not found")
    if invite.revoked_at is not None or invite.expires_at <= utc_now():
        raise ApiError(410, "invite_expired", "Invite has expired or was revoked")

    community = await db.scalar(
        select(Community).where(Community.id == invite.community_id).with_for_update()
    )
    if community is None:
        raise ApiError(404, "community_not_found", "Community not found")

    existing = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == context.user.id,
        )
    )
    if existing is None:
        member_count = await db.scalar(
            select(func.count(CommunityMember.user_id)).where(
                CommunityMember.community_id == community.id
            )
        )
        if (member_count or 0) >= settings.max_members_per_community:
            raise ApiError(409, "community_member_limit_reached", "Community member limit reached")
        db.add(
            CommunityMember(
                community_id=community.id,
                user_id=context.user.id,
                joined_at=utc_now(),
            )
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(409, "community_join_conflict", "Unable to join community") from exc
    return community
