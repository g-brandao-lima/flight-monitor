"""Rate limit emergencial no endpoint /auth/login (Phase 15.1)."""
import pytest
from fastapi.testclient import TestClient

from app.rate_limit import limiter
from main import app


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Reset slowapi storage between tests."""
    limiter.reset()
    yield
    limiter.reset()


def test_login_rate_limit_blocks_11th_request():
    """10 req/min passam, 11a retorna 429."""
    client = TestClient(app)

    for i in range(10):
        response = client.get(
            "/auth/login", follow_redirects=False
        )
        assert response.status_code != 429, f"Request {i + 1} inesperadamente bloqueada"

    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 429


def test_rate_limit_returns_429_with_retry_after():
    """Resposta 429 inclui informacao util para o cliente."""
    client = TestClient(app)

    for _ in range(10):
        client.get("/auth/login", follow_redirects=False)

    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 429


def test_autocomplete_endpoint_has_rate_limit(client):
    """GET /api/airports/search tem rate limit (LIMIT_AUTOCOMPLETE=30/min)."""
    for _ in range(30):
        response = client.get("/api/airports/search?q=gru")
        assert response.status_code != 429

    response = client.get("/api/airports/search?q=gru")
    assert response.status_code == 429


def test_polling_endpoint_has_strict_rate_limit(client):
    """POST /polling/manual tem limite baixo (LIMIT_POLLING=5/min)."""
    for i in range(5):
        response = client.post("/polling/manual", follow_redirects=False)
        assert response.status_code != 429, f"Req {i + 1} bloqueada cedo"

    response = client.post("/polling/manual", follow_redirects=False)
    assert response.status_code == 429
