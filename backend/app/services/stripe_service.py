import uuid
from typing import Optional

import stripe
from sqlalchemy.orm import Session

from app.config import settings

if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    def create_customer(self, email: str) -> str:
        """Create a Stripe customer and return the customer ID."""
        if not settings.STRIPE_SECRET_KEY:
            return f"cus_mock_{uuid.uuid4().hex[:12]}"
        customer = stripe.Customer.create(email=email)
        return customer.id

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a Stripe Checkout session and return the session URL."""
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )
        return session.url

    def create_billing_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a Stripe billing portal session and return the URL."""
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> dict:
        """Verify and construct a Stripe webhook event."""
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )


stripe_service = StripeService()
