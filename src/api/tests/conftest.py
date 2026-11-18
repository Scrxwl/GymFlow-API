"""Fixtures do pytest para a GymFlow API: banco SQLite isolado e tokens JWT (PERSONAL e STUDENT)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..database import SEED_PERSONAL_ID, SEED_STUDENT_ID, get_db, init_db_and_seed
from ..main import app
from ..models import Base, UserModel
from ..security import create_access_token


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        init_db_and_seed(session, target_engine=test_engine)
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def personal_headers(db_session: Session) -> dict[str, str]:
    personal = db_session.scalar(
        select(UserModel).where(UserModel.id == SEED_PERSONAL_ID)
    )
    assert personal is not None
    token = create_access_token(personal)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student_headers(db_session: Session) -> dict[str, str]:
    student = db_session.scalar(
        select(UserModel).where(UserModel.id == SEED_STUDENT_ID)
    )
    assert student is not None
    token = create_access_token(student)
    return {"Authorization": f"Bearer {token}"}
