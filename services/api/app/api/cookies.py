"""Authentication cookie helpers."""

from fastapi import Response

from app.config import settings
from app.infrastructure.auth.sessions import SessionCredentials


def set_auth_cookies(response: Response, credentials: SessionCredentials) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        credentials.raw_session_token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        credentials.raw_csrf_token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    response.delete_cookie("howl_oauth_state", path="/")
