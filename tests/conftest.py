import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("AGENT_TOKEN", "test-agent-token")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
os.environ.setdefault("APP_TIMEZONE", "America/Sao_Paulo")

from app.auth import hash_password
from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models import User
from app.rate_limiting import checkin_attempts, login_attempts


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    login_attempts.clear()
    checkin_attempts.clear()
    yield
    login_attempts.clear()
    checkin_attempts.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    user = User(
        username="admin",
        password_hash=hash_password("strong-password"),
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    return user
