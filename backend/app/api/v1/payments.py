import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionRead

router = APIRouter(prefix="/payments", tags=["payments"])

if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/create-checkout-session")
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe is not configured",
        )
    if not settings.STRIPE_PRICE_ID_PRO:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe price ID not configured",
        )

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    customer_id = subscription.stripe_customer_id if subscription else None
    if not customer_id:
        customer = stripe.Customer.create(email=current_user.email)
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
        mode="subscription",
        success_url="http://localhost:3000/payment/success",
        cancel_url="http://localhost:3000/payment/cancel",
        metadata={"user_id": str(current_user.id)},
    )
    return {"url": session.url}


@router.get("/subscription", response_model=SubscriptionRead)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found",
        )
    return subscription


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe webhook secret not configured",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    await _handle_stripe_event(event, db)
    return {"status": "ok"}


@router.post("/portal")
async def create_billing_portal(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe is not configured",
        )

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found",
        )

    portal_session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url="http://localhost:3000/settings",
    )
    return {"url": portal_session.url}


async def _handle_stripe_event(event: dict, db: AsyncSession) -> None:
    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        if not user_id:
            return

        result = await db.execute(
            select(Subscription).where(Subscription.user_id == uuid.UUID(user_id))
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.stripe_customer_id = customer_id
            sub.stripe_subscription_id = subscription_id
            sub.plan = "pro"
            sub.status = "active"
        else:
            sub = Subscription(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan="pro",
                status="active",
            )
            db.add(sub)
        await db.commit()

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        stripe_sub = event["data"]["object"]
        subscription_id = stripe_sub["id"]
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = stripe_sub.get("status", sub.status)
            period_end = stripe_sub.get("current_period_end")
            if period_end:
                sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
            if event_type == "customer.subscription.deleted":
                sub.plan = "free"
            await db.commit()
