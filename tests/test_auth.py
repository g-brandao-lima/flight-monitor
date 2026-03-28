"""Testes de autenticacao: OAuth routes, middleware, sessao."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import User
from main import app


class TestOAuthLogin:
    """Testes para GET /auth/login."""

    def test_login_redirects_to_google(self, unauthenticated_client: TestClient):
        """GET /auth/login redireciona para accounts.google.com."""
        response = unauthenticated_client.get("/auth/login", follow_redirects=False)
        assert response.status_code in (302, 303)
        assert "accounts.google.com" in response.headers["location"]


class TestOAuthCallback:
    """Testes para GET /auth/callback."""

    def test_callback_creates_user(self, unauthenticated_client: TestClient, db):
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
            response = unauthenticated_client.get(
                "/auth/callback", follow_redirects=False
            )

        assert response.status_code == 303
        user = db.query(User).filter(User.google_id == "google-new-user-456").first()
        assert user is not None
        assert user.email == "newuser@gmail.com"
        assert user.name == "New User"

    def test_callback_existing_user(
        self, unauthenticated_client: TestClient, db, test_user
    ):
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
            response = unauthenticated_client.get(
                "/auth/callback", follow_redirects=False
            )

        assert response.status_code == 303
        users = db.query(User).filter(User.google_id == test_user.google_id).all()
        assert len(users) == 1

    def test_callback_error_redirects_with_flash(
        self, unauthenticated_client: TestClient
    ):
        """Callback com excecao redireciona para /?msg=login_erro."""
        with patch(
            "app.auth.routes.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("OAuth error"),
        ):
            response = unauthenticated_client.get(
                "/auth/callback", follow_redirects=False
            )

        assert response.status_code == 303
        assert "msg=login_erro" in response.headers["location"]

    def test_callback_no_userinfo_redirects_with_flash(
        self, unauthenticated_client: TestClient
    ):
        """Callback sem userinfo no token redireciona para /?msg=login_erro."""
        fake_token = {"access_token": "abc123"}
        with patch(
            "app.auth.routes.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            return_value=fake_token,
        ):
            response = unauthenticated_client.get(
                "/auth/callback", follow_redirects=False
            )

        assert response.status_code == 303
        assert "msg=login_erro" in response.headers["location"]


class TestLogout:
    """Testes para GET /auth/logout."""

    def test_logout_clears_session(self, unauthenticated_client: TestClient):
        """Logout limpa sessao e redireciona para /."""
        response = unauthenticated_client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"


class TestAuthMiddleware:
    """Testes para o middleware de autenticacao."""

    def test_unauthenticated_redirect(self, unauthenticated_client: TestClient):
        """Rota protegida sem sessao redireciona para /?msg=login_required."""
        response = unauthenticated_client.get(
            "/groups/create", follow_redirects=False
        )
        assert response.status_code == 303
        assert "msg=login_required" in response.headers["location"]

    def test_public_routes_accessible(self, unauthenticated_client: TestClient):
        """GET / sem sessao retorna 200."""
        response = unauthenticated_client.get("/")
        assert response.status_code == 200

    def test_head_root_accessible(self, unauthenticated_client: TestClient):
        """HEAD / sem sessao retorna 200 (UptimeRobot)."""
        response = unauthenticated_client.head("/")
        assert response.status_code == 200

    def test_authenticated_route_works(self, authenticated_client: TestClient):
        """Rota protegida com authenticated_client retorna 200."""
        response = authenticated_client.get("/groups/create")
        assert response.status_code == 200


class TestHeaderUserUI:
    """Testes para o header condicional: avatar/nome/logout ou botao login."""

    def test_header_shows_user_info(self, db, test_user):
        """GET / com usuario logado (com foto) mostra nome e img no header."""
        from app.auth.dependencies import get_current_user

        test_user.picture_url = "https://photo.example.com/pic.jpg"
        db.commit()
        db.refresh(test_user)

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: test_user
        client = TestClient(app)
        response = client.get("/")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        html = response.text
        assert "Test" in html  # primeiro nome
        assert "https://photo.example.com/pic.jpg" in html
        assert "user-menu" in html

    def test_header_shows_initials_without_photo(
        self, authenticated_client: TestClient
    ):
        """GET / com usuario sem foto mostra div.avatar-initials com iniciais."""
        response = authenticated_client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "avatar-initials" in html
        assert "TU" in html  # Test User -> T + U

    def test_header_shows_login_button_when_not_logged(
        self, unauthenticated_client: TestClient
    ):
        """GET / sem sessao mostra botao 'Entrar com Google'."""
        response = unauthenticated_client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "Entrar com Google" in html
        assert "/auth/login" in html

    def test_header_shows_logout_on_all_pages(
        self, authenticated_client: TestClient
    ):
        """GET /groups/create com usuario logado mostra 'Sair' e link logout."""
        response = authenticated_client.get("/groups/create")
        assert response.status_code == 200
        html = response.text
        assert "Sair" in html
        assert "/auth/logout" in html
