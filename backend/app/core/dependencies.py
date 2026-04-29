from typing import Callable
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_subscription(plan: str) -> Callable:
    """Dependency factory that checks the user has at least the given plan."""

    PLAN_HIERARCHY = {"free": 0, "pro": 1, "enterprise": 2}

    async def _check(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == current_user.id)
        )
        subscription = result.scalar_one_or_none()
        user_plan = subscription.plan if subscription else "free"
        if PLAN_HIERARCHY.get(user_plan, 0) < PLAN_HIERARCHY.get(plan, 0):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"This feature requires the '{plan}' plan or higher.",
            )
        return current_user

    return _check


async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
