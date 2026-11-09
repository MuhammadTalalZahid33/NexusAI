"""Integration security tests against the real database.

These verify the tenant-isolation boundary and auth enforcement end-to-end
through the HTTP layer. They require DATABASE_URL to be configured; if it is
not, they are skipped (so CI without a DB still passes the unit suite).

Cleanup: each test removes the users/orgs it creates.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import AppEnv, LogLevel, Settings, get_settings
from app.db.models import Organization, User
from app.main import create_app

pytestmark = pytest.mark.integration


def _settings() -> Settings:
    base = get_settings()
    if not base.database_url:
        pytest.skip("DATABASE_URL not configured; skipping integration security tests.")
    return Settings(
        app_env=AppEnv.test,
        log_level=LogLevel.warning,
        database_url=base.database_url,
        jwt_secret="test-secret",
    )


@pytest.fixture
def client():
    import app.db.session as db_session

    # Reset the global engine so it binds to this test's event loop cleanly.
    db_session._engine = None
    db_session._sessionmaker = None
    with TestClient(create_app(_settings())) as c:
        yield c
    db_session._engine = None
    db_session._sessionmaker = None


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@example.com"


def _cleanup(emails: list[str]) -> None:
    """Synchronous cleanup using a short-lived engine (own event loop)."""
    import ssl

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def _run() -> None:
        engine = create_async_engine(
            _settings().async_database_url,
            connect_args={"ssl": ssl.create_default_context()},
        )
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as s:
            for email in emails:
                user = await s.scalar(select(User).where(User.email == email))
                if user:
                    await s.execute(
                        delete(Organization).where(Organization.id == user.org_id)
                    )
            await s.commit()
        await engine.dispose()

    asyncio.run(_run())


def test_unauthenticated_requests_rejected(client: TestClient) -> None:
    assert client.get("/documents").status_code == 401
    assert client.post("/chat", json={"question": "hi"}).status_code == 401


def test_cross_tenant_document_isolation(client: TestClient) -> None:
    email_a, email_b = _unique_email(), _unique_email()
    try:
        # Register two separate orgs.
        ra = client.post(
            "/auth/register",
            json={"email": email_a, "password": "password123", "organization_name": "OrgA"},
        )
        rb = client.post(
            "/auth/register",
            json={"email": email_b, "password": "password123", "organization_name": "OrgB"},
        )
        assert ra.status_code == 201 and rb.status_code == 201
        token_a = ra.json()["access_token"]
        token_b = rb.json()["access_token"]

        # Org A uploads a document.
        up = client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("a.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert up.status_code == 201
        doc_id = up.json()["id"]

        # Org B must NOT see it in its list.
        list_b = client.get("/documents", headers={"Authorization": f"Bearer {token_b}"})
        assert list_b.status_code == 200
        assert all(d["id"] != doc_id for d in list_b.json()["documents"])

        # Org B must get 404 (not 403 -> no existence leak) fetching A's doc.
        get_b = client.get(
            f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert get_b.status_code == 404

        # Org A CAN see its own document.
        get_a = client.get(
            f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token_a}"}
        )
        assert get_a.status_code == 200
    finally:
        _cleanup([email_a, email_b])


def test_login_and_me(client: TestClient) -> None:
    email = _unique_email()
    try:
        client.post(
            "/auth/register",
            json={"email": email, "password": "password123", "organization_name": "OrgC"},
        )
        login = client.post("/auth/login", json={"email": email, "password": "password123"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert me.json()["role"] == "admin"

        bad = client.post("/auth/login", json={"email": email, "password": "wrong"})
        assert bad.status_code == 401
    finally:
        _cleanup([email])
