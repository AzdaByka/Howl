"""Yandex OAuth client."""

from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(slots=True)
class YandexProfile:
    provider_user_id: str
    email: str
    display_name: str


class YandexOAuthError(RuntimeError):
    pass


async def load_yandex_profile(code: str) -> YandexProfile:
    if not settings.yandex_client_id or not settings.yandex_client_secret.get_secret_value():
        raise YandexOAuthError("Yandex OAuth is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            token_response = await client.post(
                settings.yandex_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.yandex_client_id,
                    "client_secret": settings.yandex_client_secret.get_secret_value(),
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data["access_token"]

            profile_response = await client.get(
                settings.yandex_user_info_url,
                params={"format": "json"},
                headers={"Authorization": f"OAuth {access_token}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise YandexOAuthError("Unable to load Yandex profile") from exc

    email = profile.get("default_email")
    if not email and profile.get("emails"):
        email = profile["emails"][0]
    if not email or not profile.get("id"):
        raise YandexOAuthError("Yandex profile does not contain required fields")

    display_name = profile.get("display_name") or profile.get("real_name") or email.split("@", 1)[0]
    return YandexProfile(
        provider_user_id=str(profile["id"]),
        email=email.lower().strip(),
        display_name=display_name[:64],
    )
