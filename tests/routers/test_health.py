"""Tests for GET /api/health endpoint."""


async def test_health_returns_ok(test_client):
    response = await test_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
