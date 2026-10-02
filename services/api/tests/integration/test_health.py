def test_liveness_endpoint(client) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("x-request-id")


def test_openapi_contains_backend_contract(client) -> None:
    response = client.get("/openapi.json")
    paths = response.json()["paths"]

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/communities/{community_id}/channels" in paths
    assert "/api/v1/channels/{channel_id}/voice-session" in paths
    assert "/internal/v1/events" in paths


def test_metrics_endpoint(client) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "howl_api_requests_total" in response.text
