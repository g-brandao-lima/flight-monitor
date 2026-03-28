import base64
import json

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.models import User
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _make_session_cookie(data: dict) -> str:
    """Cria um cookie de sessao assinado compativel com SessionMiddleware."""
    payload = base64.b64encode(json.dumps(data).encode("utf-8"))
    signer = TimestampSigner(settings.session_secret_key)
    return signer.sign(payload).decode("utf-8")


@pytest.fixture(name="db")
def db_fixture():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="test_user")
def test_user_fixture(db):
    user = User(
        google_id="google-test-123",
        email="test@gmail.com",
        name="Test User",
        picture_url=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(name="unauthenticated_client")
def unauthenticated_client_fixture(db):
    """Client sem sessao - para testar middleware de protecao."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="client")
def client_fixture(db, test_user):
    """Client autenticado por padrao - sessao com user_id do test_user."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    cookie_value = _make_session_cookie({"user_id": test_user.id})
    client.cookies.set("session", cookie_value)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(client, test_user):
    from app.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: test_user
    yield client
    # cleanup: client_fixture already calls dependency_overrides.clear()
