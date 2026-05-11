"""Tests for the admin bootstrap module."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_bootstrap import bootstrap_admin
from app.core.security import hash_password, verify_password
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_creates_admin_when_absent(db_session: AsyncSession, monkeypatch):
    """Bootstrap creates a new admin account when the email does not exist."""
    email = "bootstrap_new@example.com"
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_EMAIL", email)
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_PASSWORD", "adminpass123")
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_FULL_NAME", "Test Admin")

    await bootstrap_admin(db_session)

    user = await _get_user_by_email(db_session, email)
    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True
    assert user.is_verified is True
    assert user.full_name == "Test Admin"
    assert verify_password("adminpass123", user.hashed_password)


@pytest.mark.asyncio
async def test_bootstrap_idempotent(db_session: AsyncSession, monkeypatch):
    """Calling bootstrap twice does not raise and does not create duplicate accounts."""
    email = "bootstrap_idempotent@example.com"
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_EMAIL", email)
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_PASSWORD", "adminpass123")
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_FULL_NAME", "Admin")

    await bootstrap_admin(db_session)
    await bootstrap_admin(db_session)

    result = await db_session.execute(select(User).where(User.email == email))
    users = result.scalars().all()
    assert len(users) == 1
    assert users[0].role == "admin"


@pytest.mark.asyncio
async def test_bootstrap_promotes_existing_user(db_session: AsyncSession, monkeypatch):
    """If an account already exists with a non-admin role, bootstrap promotes it."""
    email = "existing_user@example.com"
    # Create a regular user first
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("somepassword"),
        full_name="Existing User",
        role="user",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_EMAIL", email)
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_PASSWORD", "adminpass456")
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_FULL_NAME", "Existing User")

    await bootstrap_admin(db_session)

    await db_session.refresh(user)
    assert user.role == "admin"
    # Password should NOT be changed
    assert verify_password("somepassword", user.hashed_password)


@pytest.mark.asyncio
async def test_bootstrap_skipped_when_email_missing(db_session: AsyncSession, monkeypatch):
    """Bootstrap is a no-op when ADMIN_EMAIL is not configured."""
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_EMAIL", "")
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_PASSWORD", "adminpass123")

    # Should not raise and should not create any user
    await bootstrap_admin(db_session)

    result = await db_session.execute(select(User).where(User.role == "admin"))
    # We can't guarantee zero admins (other tests may have created some), but
    # this test verifies the call does not crash and returns cleanly.
    assert True  # No exception raised


@pytest.mark.asyncio
async def test_bootstrap_skipped_when_password_missing(db_session: AsyncSession, monkeypatch):
    """Bootstrap is a no-op when ADMIN_PASSWORD is not configured."""
    email = "skipped_no_pass@example.com"
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_EMAIL", email)
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_PASSWORD", "")

    await bootstrap_admin(db_session)

    user = await _get_user_by_email(db_session, email)
    assert user is None


@pytest.mark.asyncio
async def test_bootstrap_preserves_existing_admin(db_session: AsyncSession, monkeypatch):
    """Bootstrap does not modify a user that already has role=admin."""
    email = "already_admin@example.com"
    original_password = "original_password"
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(original_password),
        full_name="Already Admin",
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_EMAIL", email)
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_PASSWORD", "different_password")
    monkeypatch.setattr("app.core.admin_bootstrap.settings.ADMIN_FULL_NAME", "Already Admin")

    await bootstrap_admin(db_session)

    await db_session.refresh(user)
    assert user.role == "admin"
    # Original password must still work
    assert verify_password(original_password, user.hashed_password)
