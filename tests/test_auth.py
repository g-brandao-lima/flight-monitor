"""Testes de autenticacao: OAuth routes, middleware, sessao."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models import User


class TestOAuthLogin:
    """Testes para GET /auth/login."""

    def test_login_redirects_to_google(self, client: TestClient):
        """GET /auth/login redireciona para accounts.google.com."""
        response = client.get("/auth/login", follow_redirects=False)
        assert response.status_code in (302, 303)
        assert "accounts.google.com" in response.headers["location"]


class TestOAuthCallback:
    """Testes para GET /auth/callback."""

    def test_callback_creates_user(self, client: TestClient, db):
        """Callback com token valido cria User no banco e seta sessao."""
        fake_token = {
            "userinfo": {
                "sub": "google-new-user-456",
                "email": "newuser@gmail.com",
                "name": "New User",
                "picture": "https://photo.url/pic.jpg",
            }
        }
        with patch(
            "app.auth.routes.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            return_value=fake_token,
        ):
            response = client.get("/auth/callback", follow_redirects=False)

        assert response.status_code == 303
        user = db.query(User).filter(User.google_id == "google-new-user-456").first()
        assert user is not None
        assert user.email == "newuser@gmail.com"
        assert user.name == "New User"

    def test_callback_existing_user(self, client: TestClient, db, test_user):
        """Callback com google_id existente reutiliza User (nao cria duplicata)."""
        fake_token = {
            "userinfo": {
                "sub": test_user.google_id,
                "email": test_user.email,
                "name": test_user.name,
                "picture": None,
            }
        }
        with patch(
            "app.auth.routes.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            return_value=fake_token,
        ):
            response = client.get("/auth/callback", follow_redirects=False)

        assert response.status_code == 303
        users = db.query(User).filter(User.google_id == test_user.google_id).all()
        assert len(users) == 1

    def test_callback_error_redirects_with_flash(self, client: TestClient):
        """Callback com excecao redireciona para /?msg=login_erro."""
        with patch(
            "app.auth.routes.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("OAuth error"),
        ):
            response = client.get("/auth/callback", follow_redirects=False)

        assert response.status_code == 303
        assert "msg=login_erro" in response.headers["location"]

    def test_callback_no_userinfo_redirects_with_flash(self, client: TestClient):
        """Callback sem userinfo no token redireciona para /?msg=login_erro."""
        fake_token = {"access_token": "abc123"}
        with patch(
            "app.auth.routes.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            return_value=fake_token,
        ):
            response = client.get("/auth/callback", follow_redirects=False)

        assert response.status_code == 303
        assert "msg=login_erro" in response.headers["location"]


class TestLogout:
    """Testes para GET /auth/logout."""

    def test_logout_clears_session(self, client: TestClient):
        """Logout limpa sessao e redireciona para /."""
        response = client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"


class TestAuthMiddleware:
    """Testes para o middleware de autenticacao."""

    def test_unauthenticated_redirect(self, client: TestClient):
        """Rota protegida sem sessao redireciona para /?msg=login_required."""
        response = client.get("/groups/create", follow_redirects=False)
        assert response.status_code == 303
        assert "msg=login_required" in response.headers["location"]

    def test_public_routes_accessible(self, client: TestClient):
        """GET / sem sessao retorna 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_head_root_accessible(self, client: TestClient):
        """HEAD / sem sessao retorna 200 (UptimeRobot)."""
        response = client.head("/")
        assert response.status_code == 200

    def test_authenticated_route_works(self, authenticated_client: TestClient):
        """Rota protegida com authenticated_client retorna 200."""
        response = authenticated_client.get("/groups/create")
        assert response.status_code == 200
