from datetime import UTC, datetime
from uuid import uuid4

from app.config import settings


def test_realtime_subscription_receives_media_event(client) -> None:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"realtime-{uuid4().hex}@example.com",
            "password": "correct horse battery staple",
            "display_name": "Realtime User",
        },
    )
    assert register.status_code == 201
    user_id = register.json()["user"]["id"]
    headers = {"X-CSRF-Token": client.cookies.get("howl_csrf")}

    community = client.post(
        "/api/v1/communities",
        json={"name": f"Realtime Community {uuid4().hex}"},
        headers=headers,
    )
    assert community.status_code == 201
    community_id = community.json()["id"]

    channel = client.post(
        f"/api/v1/communities/{community_id}/channels",
        json={"name": "General"},
        headers=headers,
    )
    assert channel.status_code == 201
    channel_id = channel.json()["id"]

    with client.websocket_connect("/api/v1/realtime") as websocket:
        websocket.send_json(
            {
                "type": "subscribe",
                "community_id": community_id,
                "channel_id": channel_id,
            }
        )
        subscribed = websocket.receive_json()
        assert subscribed["type"] == "subscribed"

        event_id = str(uuid4())
        event = client.post(
            "/internal/v1/events",
            headers={"X-Internal-Token": settings.media_internal_token.get_secret_value()},
            json={
                "event_id": event_id,
                "type": "participant.joined",
                "occurred_at": datetime.now(UTC).isoformat(),
                "community_id": community_id,
                "channel_id": channel_id,
                "user_id": user_id,
                "payload": {"display_name": "Realtime User"},
            },
        )
        assert event.status_code == 202

        received = websocket.receive_json()
        assert received["event_id"] == event_id
        assert received["type"] == "participant.joined"
