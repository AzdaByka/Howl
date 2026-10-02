"""Opaque cookie session management."""

import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.auth.tokens import hash_token
from app.infrastructure.database.models import Session, User


@dataclass(slots=True)
class AuthContext:
    user: User
    session: Session


@dataclass(slots=True)
class SessionCredentials:
    raw_session_token: str
    raw_csrf_token: str
    session: Session


def _now() -> datetime:
    return datetime.now(UTC)


async def create_session(
    db: AsyncSession,
    user: User,
    request: Request | None = None,
) -> SessionCredentials:
    raw_session = secrets.token_urlsafe(32)
    raw_csrf = secrets.token_urlsafe(32)
    now = _now()
    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_session),
        csrf_token_hash=hash_token(raw_csrf),
        expires_at=now + timedelta(days=settings.session_ttl_days),
        last_seen_at=now,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(session)
    await db.flush()
    return SessionCredentials(raw_session, raw_csrf, session)


async def get_auth_context(db: AsyncSession, raw_session_token: str | None) -> AuthContext | None:
    if not raw_session_token:
        return None

    result = await db.execute(
        select(Session, User)
        .join(User, User.id == Session.user_id)
        .where(Session.token_hash == hash_token(raw_session_token))
    )
    row = result.one_or_none()
    if row is None:
        return None

    session, user = row
    if session.expires_at <= _now() or not user.is_active:
        return None
    return AuthContext(user=user, session=session)


async def delete_session(db: AsyncSession, session: Session) -> None:
    await db.execute(delete(Session).where(Session.id == session.id))


def valid_csrf(context: AuthContext, header_token: str | None, cookie_token: str | None) -> bool:
    if not header_token or not cookie_token:
        return False
    if not hmac.compare_digest(header_token, cookie_token):
        return False
    return hmac.compare_digest(hash_token(header_token), context.session.csrf_token_hash)
