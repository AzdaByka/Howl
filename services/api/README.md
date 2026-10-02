# API service

Основной backend на Python 3.14.

Зона ответственности:

- HTTP API;
- авторизация и cookie-сессии;
- Yandex OAuth;
- сообщества, каналы и приглашения;
- WebSocket-события и WebRTC-сигналинг;
- PostgreSQL и миграции.

## Разработка

```bash
uv sync --dev
uv run alembic upgrade head
uv run pytest
uv run ruff check app migrations tests
```

Основные публичные группы маршрутов:

- `/api/v1/auth/*` — регистрация, login, logout, текущий пользователь и Yandex OAuth;
- `/api/v1/communities/*` — сообщества, приглашения и membership;
- `/api/v1/communities/{community_id}/channels` — голосовые каналы;
- `/api/v1/channels/{channel_id}/voice-session` — выдача media-сессии;
- `/api/v1/realtime` — realtime WebSocket;
- `/internal/v1/events` — callback от media-сервиса.

Media-сервис получает команды через внутренний HTTP API:

```text
POST   /internal/v1/voice-sessions
DELETE /internal/v1/voice-sessions/{session_id}
POST   /internal/v1/events
```
