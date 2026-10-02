"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.config import settings
from app.infrastructure.auth.sessions import AuthContext, get_auth_context, valid_csrf
from app.infrastructure.database.session import get_db


async def get_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    context = await get_auth_context(db, request.cookies.get(settings.session_cookie_name))
    if context is None:
        raise ApiError(401, "not_authenticated", "Authentication is required")
    return context


async def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_auth),
) -> AuthContext:
    if not valid_csrf(
        context,
        request.headers.get("X-CSRF-Token"),
        request.cookies.get("howl_csrf"),
    ):
        raise ApiError(403, "csrf_invalid", "CSRF validation failed")
    return context
