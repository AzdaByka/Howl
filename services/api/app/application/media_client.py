"""Internal HTTP client for the media service."""

from typing import Any

import httpx

from app.api.schemas import MediaSessionRequest, MediaSessionResponse
from app.config import settings


class MediaServiceError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class MediaServiceClient:
    def __init__(self, base_url: str | None = None, internal_token: str | None = None) -> None:
        self.base_url = (base_url or settings.media_service_url).rstrip("/")
        self.internal_token = internal_token or settings.media_internal_token.get_secret_value()

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {"X-Internal-Token": self.internal_token}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def create_voice_session(self, request: MediaSessionRequest) -> MediaSessionResponse:
        try:
            async with httpx.AsyncClient(timeout=settings.media_timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/internal/v1/voice-sessions",
                    json=request.model_dump(mode="json"),
                    headers=self._headers(request.idempotency_key),
                )
        except httpx.HTTPError as exc:
            raise MediaServiceError(
                "media_service_unavailable", "Media service is unavailable"
            ) from exc

        if response.status_code == 409:
            raise MediaServiceError("voice_channel_full", "Voice channel is full", 409)
        if response.status_code >= 500:
            raise MediaServiceError("media_service_unavailable", "Media service is unavailable")
        if response.is_error:
            raise MediaServiceError("media_session_rejected", "Media session was rejected", 502)

        try:
            return MediaSessionResponse.model_validate(response.json())
        except ValueError as exc:
            raise MediaServiceError(
                "media_service_invalid_response", "Invalid media service response", 502
            ) from exc

    async def delete_voice_session(self, session_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=settings.media_timeout_seconds) as client:
                response = await client.delete(
                    f"{self.base_url}/internal/v1/voice-sessions/{session_id}",
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            raise MediaServiceError(
                "media_service_unavailable", "Media service is unavailable"
            ) from exc

        if response.status_code >= 500:
            raise MediaServiceError("media_service_unavailable", "Media service is unavailable")
        if response.status_code not in (200, 204, 404):
            raise MediaServiceError(
                "media_session_rejected", "Media session termination was rejected", 502
            )


def media_error_to_api_error(error: MediaServiceError) -> Any:
    from app.api.errors import ApiError

    return ApiError(error.status_code, error.code, error.message)
