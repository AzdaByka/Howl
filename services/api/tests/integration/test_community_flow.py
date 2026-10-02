from uuid import uuid4


def register(client, label: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{label}-{uuid4().hex}@example.com",
            "password": "correct horse battery staple",
            "display_name": label,
        },
    )
    assert response.status_code == 201, response.text
    return client.cookies.get("howl_csrf")


def csrf_headers(client) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("howl_csrf")}


def test_owner_invite_member_and_channel_flow(client) -> None:
    owner_csrf = register(client, "owner")
    owner_headers = {"X-CSRF-Token": owner_csrf}

    community_response = client.post(
        "/api/v1/communities",
        json={"name": f"Community {uuid4().hex}"},
        headers=owner_headers,
    )
    assert community_response.status_code == 201, community_response.text
    community_id = community_response.json()["id"]

    invite_response = client.post(
        f"/api/v1/communities/{community_id}/invites",
        headers=owner_headers,
    )
    assert invite_response.status_code == 201, invite_response.text
    invite_token = invite_response.json()["token"]

    channel_response = client.post(
        f"/api/v1/communities/{community_id}/channels",
        json={"name": "General"},
        headers=owner_headers,
    )
    assert channel_response.status_code == 201, channel_response.text
    channel_id = channel_response.json()["id"]

    member_csrf = register(client, "member")
    member_headers = {"X-CSRF-Token": member_csrf}

    accept_response = client.post(
        f"/api/v1/invites/{invite_token}/accept",
        headers=member_headers,
    )
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["id"] == community_id

    communities_response = client.get("/api/v1/me/communities")
    assert communities_response.status_code == 200
    assert communities_response.json()[0]["member_count"] == 2

    channels_response = client.get(f"/api/v1/communities/{community_id}/channels")
    assert channels_response.status_code == 200
    assert channels_response.json()[0]["id"] == channel_id

    forbidden_response = client.post(
        f"/api/v1/communities/{community_id}/channels",
        json={"name": "Forbidden"},
        headers=member_headers,
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["error"]["code"] == "community_owner_required"

    media_response = client.post(
        f"/api/v1/channels/{channel_id}/voice-session",
        headers=member_headers,
    )
    assert media_response.status_code == 503
    assert media_response.json()["error"]["code"] == "media_service_unavailable"
