"""Authentication routes."""

import hmac
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.cookies import clear_auth_cookies, set_auth_cookies
from app.api.dependencies import get_auth, require_csrf
from app.api.errors import ApiError
from app.api.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.config import settings
from app.infrastructure.auth.passwords import hash_password, verify_password
from app.infrastructure.auth.sessions import (
    AuthContext,
    create_session,
    delete_session,
)
from app.infrastructure.auth.tokens import hash_token
from app.infrastructure.database.models import OAuthAccount, User
from app.infrastructure.database.session import get_db
from app.infrastructure.oauth.yandex import YandexOAuthError, load_yandex_profile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    email = str(payload.email).lower().strip()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ApiError(409, "email_already_registered", "Email is already registered")

    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.flush()
        credentials = await create_session(db, user, request)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if "uq_users_email" in str(exc.orig):
            raise ApiError(409, "email_already_registered", "Email is already registered") from exc
        raise

    set_auth_cookies(response, credentials)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    email = str(payload.email).lower().strip()
    user = await db.scalar(select(User).where(User.email == email))
    if (
        user is None
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        raise ApiError(401, "invalid_credentials", "Invalid email or password")
    if not user.is_active:
        raise ApiError(403, "user_inactive", "User account is inactive")

    credentials = await create_session(db, user, request)
    await db.commit()
    set_auth_cookies(response, credentials)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await delete_session(db, context.session)
    await db.commit()
    clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserResponse)
async def me(context: AuthContext = Depends(get_auth)) -> UserResponse:
    return UserResponse.model_validate(context.user)


@router.get("/csrf")
async def csrf(
    request: Request,
    response: Response,
    context: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    token = request.cookies.get(settings.csrf_cookie_name)
    if not token or not hmac.compare_digest(hash_token(token), context.session.csrf_token_hash):
        token = secrets.token_urlsafe(32)
        context.session.csrf_token_hash = hash_token(token)
        await db.commit()
        response.set_cookie(
            settings.csrf_cookie_name,
            token,
            max_age=settings.session_ttl_days * 24 * 60 * 60,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )
    return {"csrf_token": token}


@router.get("/yandex/start")
async def yandex_start() -> RedirectResponse:
    if not settings.yandex_client_id:
        raise ApiError(503, "oauth_not_configured", "Yandex OAuth is not configured")

    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.yandex_client_id,
            "redirect_uri": settings.yandex_redirect_uri,
            "state": state,
        }
    )
    response = RedirectResponse(f"{settings.yandex_authorize_url}?{query}", status_code=302)
    response.set_cookie(
        "howl_oauth_state",
        state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/yandex/callback")
async def yandex_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    saved_state = request.cookies.get("howl_oauth_state")
    if not code or not state or not saved_state or not hmac.compare_digest(state, saved_state):
        raise ApiError(400, "oauth_state_invalid", "OAuth state is invalid")

    try:
        profile = await load_yandex_profile(code)
    except YandexOAuthError as exc:
        raise ApiError(502, "oauth_provider_error", "Yandex OAuth request failed") from exc

    account = await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == "yandex",
            OAuthAccount.provider_user_id == profile.provider_user_id,
        )
    )
    user = await db.get(User, account.user_id) if account else None

    if user is None:
        user = await db.scalar(select(User).where(User.email == profile.email))
        if user is None:
            user = User(email=profile.email, display_name=profile.display_name)
            db.add(user)
            await db.flush()
        if account is None:
            db.add(
                OAuthAccount(
                    user_id=user.id,
                    provider="yandex",
                    provider_user_id=profile.provider_user_id,
                    provider_email=profile.email,
                )
            )

    credentials = await create_session(db, user, request)
    await db.commit()
    redirect = RedirectResponse(
        f"{settings.frontend_url}/oauth/callback?status=success", status_code=303
    )
    set_auth_cookies(redirect, credentials)
    redirect.delete_cookie("howl_oauth_state", path="/")
    return redirect
