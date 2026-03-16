"""
RealDeal AI - Subscription Service

Manages user subscriptions via Stripe: plan tiers, checkout sessions,
customer portal, webhook handling, and usage limit enforcement.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import stripe

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
APP_URL = os.getenv("APP_URL", "https://app.realdeal-ai.com")

stripe.api_key = STRIPE_SECRET_KEY


class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class PlanLimits:
    """Usage limits per subscription tier."""

    markets: int
    alerts: int
    daily_property_views: int
    ai_summaries_per_month: int
    csv_exports: bool
    api_access: bool
    priority_support: bool
    price_monthly: float
    price_yearly: float  # annual price (total, not per-month)
    stripe_price_id_monthly: str
    stripe_price_id_yearly: str


# Plan definitions
PLAN_CONFIGS: dict[PlanTier, PlanLimits] = {
    PlanTier.FREE: PlanLimits(
        markets=1,
        alerts=1,
        daily_property_views=10,
        ai_summaries_per_month=5,
        csv_exports=False,
        api_access=False,
        priority_support=False,
        price_monthly=0,
        price_yearly=0,
        stripe_price_id_monthly="",
        stripe_price_id_yearly="",
    ),
    PlanTier.STARTER: PlanLimits(
        markets=3,
        alerts=5,
        daily_property_views=50,
        ai_summaries_per_month=50,
        csv_exports=True,
        api_access=False,
        priority_support=False,
        price_monthly=29.0,
        price_yearly=290.0,
        stripe_price_id_monthly=os.getenv("STRIPE_STARTER_MONTHLY", "price_starter_monthly"),
        stripe_price_id_yearly=os.getenv("STRIPE_STARTER_YEARLY", "price_starter_yearly"),
    ),
    PlanTier.PRO: PlanLimits(
        markets=10,
        alerts=25,
        daily_property_views=500,
        ai_summaries_per_month=500,
        csv_exports=True,
        api_access=True,
        priority_support=False,
        price_monthly=79.0,
        price_yearly=790.0,
        stripe_price_id_monthly=os.getenv("STRIPE_PRO_MONTHLY", "price_pro_monthly"),
        stripe_price_id_yearly=os.getenv("STRIPE_PRO_YEARLY", "price_pro_yearly"),
    ),
    PlanTier.ENTERPRISE: PlanLimits(
        markets=999,
        alerts=999,
        daily_property_views=99999,
        ai_summaries_per_month=99999,
        csv_exports=True,
        api_access=True,
        priority_support=True,
        price_monthly=199.0,
        price_yearly=1990.0,
        stripe_price_id_monthly=os.getenv("STRIPE_ENTERPRISE_MONTHLY", "price_enterprise_monthly"),
        stripe_price_id_yearly=os.getenv("STRIPE_ENTERPRISE_YEARLY", "price_enterprise_yearly"),
    ),
}


class SubscriptionService:
    """Manage user subscriptions and enforce tier-based usage limits."""

    def __init__(self):
        if not STRIPE_SECRET_KEY:
            logger.warning("Stripe API key not configured")

    # ------------------------------------------------------------------
    # Plan information
    # ------------------------------------------------------------------

    def get_plan_limits(self, tier: PlanTier) -> PlanLimits:
        """Return the limits for a given plan tier."""
        return PLAN_CONFIGS[tier]

    def get_all_plans(self) -> list[dict[str, Any]]:
        """Return all available plans with details."""
        plans = []
        for tier, limits in PLAN_CONFIGS.items():
            plans.append(
                {
                    "tier": tier.value,
                    "name": tier.value.title(),
                    "price_monthly": limits.price_monthly,
                    "price_yearly": limits.price_yearly,
                    "price_yearly_monthly": round(limits.price_yearly / 12, 2) if limits.price_yearly > 0 else 0,
                    "markets": limits.markets,
                    "alerts": limits.alerts,
                    "daily_property_views": limits.daily_property_views,
                    "ai_summaries_per_month": limits.ai_summaries_per_month,
                    "csv_exports": limits.csv_exports,
                    "api_access": limits.api_access,
                    "priority_support": limits.priority_support,
                }
            )
        return plans

    # ------------------------------------------------------------------
    # Limit checking
    # ------------------------------------------------------------------

    def check_limit(
        self, user_id: str, resource: str, current_usage: int = 0
    ) -> dict[str, Any]:
        """
        Check if a user has exceeded a specific resource limit.

        Returns {
            "allowed": bool,
            "limit": int,
            "used": int,
            "remaining": int,
            "tier": str,
        }
        """
        tier = self._get_user_tier(user_id)
        limits = PLAN_CONFIGS[tier]

        limit_map = {
            "markets": limits.markets,
            "alerts": limits.alerts,
            "daily_property_views": limits.daily_property_views,
            "ai_summaries": limits.ai_summaries_per_month,
        }

        max_allowed = limit_map.get(resource, 0)
        remaining = max(0, max_allowed - current_usage)

        return {
            "allowed": current_usage < max_allowed,
            "limit": max_allowed,
            "used": current_usage,
            "remaining": remaining,
            "tier": tier.value,
        }

    def check_feature(self, user_id: str, feature: str) -> bool:
        """Check if a user's plan includes a specific feature."""
        tier = self._get_user_tier(user_id)
        limits = PLAN_CONFIGS[tier]

        feature_map = {
            "csv_exports": limits.csv_exports,
            "api_access": limits.api_access,
            "priority_support": limits.priority_support,
        }
        return feature_map.get(feature, False)

    # ------------------------------------------------------------------
    # Stripe Checkout
    # ------------------------------------------------------------------

    def create_checkout_session(
        self,
        user_id: str,
        tier: PlanTier,
        billing_period: str = "monthly",  # "monthly" or "yearly"
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a Stripe Checkout session for upgrading to a plan.

        Returns {"session_id": str, "checkout_url": str}
        """
        limits = PLAN_CONFIGS[tier]
        price_id = (
            limits.stripe_price_id_monthly
            if billing_period == "monthly"
            else limits.stripe_price_id_yearly
        )

        if not price_id:
            raise ValueError(f"No Stripe price configured for {tier.value} {billing_period}")

        customer_id = self._get_or_create_stripe_customer(user_id)

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url or f"{APP_URL}/settings/billing?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url or f"{APP_URL}/pricing",
                metadata={
                    "user_id": user_id,
                    "tier": tier.value,
                    "billing_period": billing_period,
                },
                allow_promotion_codes=True,
                billing_address_collection="required",
                subscription_data={
                    "metadata": {
                        "user_id": user_id,
                        "tier": tier.value,
                    },
                    "trial_period_days": 7 if tier != PlanTier.FREE else None,
                },
            )

            logger.info(
                "Checkout session created for user %s, tier %s: %s",
                user_id, tier.value, session.id,
            )

            return {
                "session_id": session.id,
                "checkout_url": session.url,
            }

        except stripe.error.StripeError as exc:
            logger.error("Stripe checkout creation failed: %s", exc)
            raise

    def create_customer_portal_session(
        self, user_id: str, return_url: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a Stripe Customer Portal session for managing billing."""
        customer_id = self._get_or_create_stripe_customer(user_id)

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url or f"{APP_URL}/settings/billing",
            )

            return {
                "session_id": session.id,
                "portal_url": session.url,
            }

        except stripe.error.StripeError as exc:
            logger.error("Stripe portal creation failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def get_subscription_status(self, user_id: str) -> dict[str, Any]:
        """Get the current subscription status for a user."""
        sub_data = self._get_user_subscription(user_id)
        if not sub_data:
            return {
                "tier": PlanTier.FREE.value,
                "status": "active",
                "is_trial": False,
                "current_period_end": None,
                "cancel_at_period_end": False,
            }

        return sub_data

    def cancel_subscription(self, user_id: str, at_period_end: bool = True) -> dict[str, Any]:
        """Cancel a user's subscription. By default cancels at period end."""
        sub_data = self._get_user_subscription(user_id)
        if not sub_data or not sub_data.get("stripe_subscription_id"):
            raise ValueError("No active subscription found")

        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    sub_data["stripe_subscription_id"],
                    cancel_at_period_end=True,
                )
                logger.info("Subscription set to cancel at period end for user %s", user_id)
            else:
                subscription = stripe.Subscription.delete(
                    sub_data["stripe_subscription_id"],
                )
                self._update_user_tier(user_id, PlanTier.FREE)
                logger.info("Subscription cancelled immediately for user %s", user_id)

            return {
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "current_period_end": datetime.fromtimestamp(
                    subscription.current_period_end
                ).isoformat(),
            }

        except stripe.error.StripeError as exc:
            logger.error("Subscription cancellation failed: %s", exc)
            raise

    def change_plan(
        self, user_id: str, new_tier: PlanTier, billing_period: str = "monthly"
    ) -> dict[str, Any]:
        """Change a user's subscription to a different plan."""
        sub_data = self._get_user_subscription(user_id)
        if not sub_data or not sub_data.get("stripe_subscription_id"):
            # No existing subscription, create a new checkout
            return self.create_checkout_session(user_id, new_tier, billing_period)

        new_limits = PLAN_CONFIGS[new_tier]
        new_price_id = (
            new_limits.stripe_price_id_monthly
            if billing_period == "monthly"
            else new_limits.stripe_price_id_yearly
        )

        try:
            subscription = stripe.Subscription.retrieve(
                sub_data["stripe_subscription_id"]
            )

            # Update the subscription with the new price
            updated = stripe.Subscription.modify(
                subscription.id,
                items=[
                    {
                        "id": subscription["items"]["data"][0].id,
                        "price": new_price_id,
                    }
                ],
                proration_behavior="create_prorations",
                metadata={
                    "user_id": user_id,
                    "tier": new_tier.value,
                },
            )

            self._update_user_tier(user_id, new_tier)

            logger.info(
                "Plan changed for user %s: %s -> %s",
                user_id, sub_data.get("tier"), new_tier.value,
            )

            return {
                "status": updated.status,
                "tier": new_tier.value,
                "current_period_end": datetime.fromtimestamp(
                    updated.current_period_end
                ).isoformat(),
            }

        except stripe.error.StripeError as exc:
            logger.error("Plan change failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Webhook handling
    # ------------------------------------------------------------------

    def handle_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """
        Process a Stripe webhook event.

        Handles:
        - checkout.session.completed
        - customer.subscription.updated
        - customer.subscription.deleted
        - invoice.payment_succeeded
        - invoice.payment_failed
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            logger.error("Webhook signature verification failed: %s", exc)
            raise

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info("Processing webhook: %s", event_type)

        handler_map = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_succeeded": self._handle_payment_succeeded,
            "invoice.payment_failed": self._handle_payment_failed,
        }

        handler = handler_map.get(event_type)
        if handler:
            return handler(data)

        logger.debug("Unhandled webhook event type: %s", event_type)
        return {"status": "ignored", "event_type": event_type}

    def _handle_checkout_completed(self, session: dict) -> dict[str, Any]:
        """Handle successful checkout: activate subscription."""
        user_id = session.get("metadata", {}).get("user_id", "")
        tier_str = session.get("metadata", {}).get("tier", "starter")

        try:
            tier = PlanTier(tier_str)
        except ValueError:
            tier = PlanTier.STARTER

        subscription_id = session.get("subscription", "")
        customer_id = session.get("customer", "")

        # Update user in database
        self._update_user_tier(user_id, tier)
        self._store_subscription(
            user_id=user_id,
            stripe_subscription_id=subscription_id,
            stripe_customer_id=customer_id,
            tier=tier,
            status="active",
        )

        # Send confirmation email
        from app.services.notification import NotificationService
        notification_svc = NotificationService()
        user_email = self._get_user_email(user_id)
        limits = PLAN_CONFIGS[tier]
        if user_email:
            notification_svc.send_subscription_confirmation(
                user_email, tier.value.title(), limits.price_monthly
            )

        logger.info("Checkout completed for user %s, tier %s", user_id, tier.value)
        return {"status": "activated", "user_id": user_id, "tier": tier.value}

    def _handle_subscription_updated(self, subscription: dict) -> dict[str, Any]:
        """Handle subscription changes (upgrades, downgrades, renewals)."""
        user_id = subscription.get("metadata", {}).get("user_id", "")
        tier_str = subscription.get("metadata", {}).get("tier", "")
        status = subscription.get("status", "")

        if user_id and tier_str:
            try:
                tier = PlanTier(tier_str)
                self._update_user_tier(user_id, tier)
            except ValueError:
                pass

        logger.info("Subscription updated for user %s: status=%s", user_id, status)
        return {"status": "updated", "user_id": user_id}

    def _handle_subscription_deleted(self, subscription: dict) -> dict[str, Any]:
        """Handle subscription cancellation / expiry."""
        user_id = subscription.get("metadata", {}).get("user_id", "")

        if user_id:
            self._update_user_tier(user_id, PlanTier.FREE)

        logger.info("Subscription deleted for user %s, downgraded to free", user_id)
        return {"status": "cancelled", "user_id": user_id}

    def _handle_payment_succeeded(self, invoice: dict) -> dict[str, Any]:
        """Handle successful payment."""
        customer_id = invoice.get("customer", "")
        amount = invoice.get("amount_paid", 0) / 100  # cents to dollars

        logger.info("Payment succeeded for customer %s: $%.2f", customer_id, amount)
        return {"status": "paid", "amount": amount}

    def _handle_payment_failed(self, invoice: dict) -> dict[str, Any]:
        """Handle failed payment: notify user, may need to downgrade."""
        customer_id = invoice.get("customer", "")
        attempt = invoice.get("attempt_count", 0)

        logger.warning(
            "Payment failed for customer %s (attempt %d)", customer_id, attempt
        )

        # After 3 failed attempts, downgrade to free
        if attempt >= 3:
            user_id = self._get_user_by_customer(customer_id)
            if user_id:
                self._update_user_tier(user_id, PlanTier.FREE)
                logger.warning("User %s downgraded to free after payment failures", user_id)

        return {"status": "payment_failed", "attempt": attempt}

    # ------------------------------------------------------------------
    # Stripe customer management
    # ------------------------------------------------------------------

    def _get_or_create_stripe_customer(self, user_id: str) -> str:
        """Get existing Stripe customer ID or create a new one."""
        # Check database first
        customer_id = self._get_stripe_customer_id(user_id)
        if customer_id:
            return customer_id

        # Create new Stripe customer
        user_email = self._get_user_email(user_id)
        user_name = self._get_user_name(user_id)

        try:
            customer = stripe.Customer.create(
                email=user_email,
                name=user_name,
                metadata={"user_id": user_id},
            )
            # Store in database
            self._store_stripe_customer_id(user_id, customer.id)
            return customer.id

        except stripe.error.StripeError as exc:
            logger.error("Stripe customer creation failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Database interface stubs
    # ------------------------------------------------------------------

    def _get_user_tier(self, user_id: str) -> PlanTier:
        """Get user's current subscription tier from database."""
        # In production: SELECT tier FROM subscriptions WHERE user_id = ?
        return PlanTier.FREE

    def _update_user_tier(self, user_id: str, tier: PlanTier) -> None:
        """Update user's subscription tier in database."""
        logger.debug("Updating tier for user %s to %s", user_id, tier.value)

    def _get_user_subscription(self, user_id: str) -> Optional[dict]:
        """Get full subscription data from database."""
        return None

    def _store_subscription(self, **kwargs) -> None:
        """Store subscription record in database."""
        logger.debug("Storing subscription: %s", kwargs)

    def _get_stripe_customer_id(self, user_id: str) -> Optional[str]:
        """Look up Stripe customer ID from database."""
        return None

    def _store_stripe_customer_id(self, user_id: str, customer_id: str) -> None:
        """Store Stripe customer ID in database."""
        logger.debug("Storing Stripe customer %s for user %s", customer_id, user_id)

    def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user email from database."""
        return None

    def _get_user_name(self, user_id: str) -> Optional[str]:
        """Get user name from database."""
        return None

    def _get_user_by_customer(self, customer_id: str) -> Optional[str]:
        """Look up user ID by Stripe customer ID."""
        return None
