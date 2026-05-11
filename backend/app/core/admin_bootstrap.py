"""
Admin bootstrap: create or promote the initial admin user on startup.

Behavior
--------
- Runs only when both ``ADMIN_EMAIL`` and ``ADMIN_PASSWORD`` are set.
- If no account with that e-mail exists: creates one with ``role="admin"``,
  a bcrypt-hashed password, and marks it active + verified.
- If an account already exists: preserves the password and all other fields,
  but ensures ``role`` is set to ``"admin"`` (idempotent promotion).
- Safe to call on every startup — it never creates duplicates.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def bootstrap_admin(db: AsyncSession) -> None:
    """Create or promote the admin user configured via environment variables."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        logger.debug("Admin bootstrap skipped: ADMIN_EMAIL or ADMIN_PASSWORD not set.")
        return

    result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
    existing = result.scalar_one_or_none()

    if existing is None:
        admin = User(
            id=uuid.uuid4(),
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            full_name=settings.ADMIN_FULL_NAME or "Administrator",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        await db.commit()
        logger.info("Admin account created: %s", settings.ADMIN_EMAIL)
    else:
        if existing.role != "admin":
            existing.role = "admin"
            db.add(existing)
            await db.commit()
            logger.info(
                "Existing account promoted to admin: %s", settings.ADMIN_EMAIL
            )
        else:
            logger.debug(
                "Admin account already exists, no changes needed: %s",
                settings.ADMIN_EMAIL,
            )
