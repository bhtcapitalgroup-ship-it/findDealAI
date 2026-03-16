"""Tests for the subscription service (app.services.subscription)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.subscription import (
    PLAN_CONFIGS,
    PlanLimits,
    PlanTier,
    SubscriptionService,
)


@pytest.fixture
def svc() -> SubscriptionService:
    return SubscriptionService()


class TestFreeTierLimits:
    """Tests for FREE plan limits."""

    def test_free_tier_limits(self, svc: SubscriptionService):
        """Free tier should have restricted limits."""
        limits = svc.get_plan_limits(PlanTier.FREE)
        assert limits.markets == 1
        assert limits.alerts == 1
        assert limits.daily_property_views == 10
        assert limits.ai_summaries_per_month == 5
        assert limits.csv_exports is False
        assert limits.api_access is False
        assert limits.price_monthly == 0

    def test_free_tier_check_limit_exceeded(self, svc: SubscriptionService):
        """Using more than 10 daily views on free should be disallowed."""
        result = svc.check_limit("user-free", "daily_property_views", current_usage=11)
        assert result["allowed"] is False
        assert result["remaining"] == 0

    def test_free_tier_check_limit_within(self, svc: SubscriptionService):
        """Using fewer than 10 daily views on free should be allowed."""
        result = svc.check_limit("user-free", "daily_property_views", current_usage=5)
        assert result["allowed"] is True
        assert result["remaining"] == 5


class TestProTierLimits:
    """Tests for PRO plan limits."""

    def test_pro_tier_limits(self, svc: SubscriptionService):
        """Pro tier should have expanded limits."""
        limits = svc.get_plan_limits(PlanTier.PRO)
        assert limits.markets == 10
        assert limits.alerts == 25
        assert limits.daily_property_views == 500
        assert limits.csv_exports is True
        assert limits.api_access is True
        assert limits.price_monthly == 79.0


class TestEnterpriseLimits:
    """Tests for ENTERPRISE (unlimited) plan limits."""

    def test_pro_plus_unlimited(self, svc: SubscriptionService):
        """Enterprise tier should have effectively unlimited access."""
        limits = svc.get_plan_limits(PlanTier.ENTERPRISE)
        assert limits.daily_property_views == 99999
        assert limits.ai_summaries_per_month == 99999
        assert limits.csv_exports is True
        assert limits.api_access is True
        assert limits.priority_support is True


class TestDailyDealCountReset:
    """Tests for daily usage count behavior."""

    def test_daily_deal_count_reset(self, svc: SubscriptionService):
        """After a reset (usage=0), the user should have full remaining."""
        result = svc.check_limit("user-reset", "daily_property_views", current_usage=0)
        assert result["allowed"] is True
        assert result["remaining"] == result["limit"]


class TestFeatureChecks:
    """Tests for feature-gated access."""

    def test_free_no_csv_export(self, svc: SubscriptionService):
        """Free tier should not have CSV export access."""
        assert svc.check_feature("user-free", "csv_exports") is False

    def test_free_no_api_access(self, svc: SubscriptionService):
        """Free tier should not have API access."""
        assert svc.check_feature("user-free", "api_access") is False


class TestStripeCheckoutSessionCreation:
    """Tests for Stripe checkout session creation (mocked)."""

    @patch("app.services.subscription.stripe")
    def test_stripe_checkout_session_creation(self, mock_stripe, svc):
        """create_checkout_session should call Stripe with correct params."""
        # Mock the stripe customer lookup
        svc._get_or_create_stripe_customer = MagicMock(return_value="cus_test123")

        mock_session = MagicMock()
        mock_session.id = "cs_test_abc"
        mock_session.url = "https://checkout.stripe.com/cs_test_abc"
        mock_stripe.checkout.Session.create.return_value = mock_session

        result = svc.create_checkout_session(
            user_id="user-123",
            tier=PlanTier.PRO,
            billing_period="monthly",
        )

        assert result["session_id"] == "cs_test_abc"
        assert result["checkout_url"] == "https://checkout.stripe.com/cs_test_abc"
        mock_stripe.checkout.Session.create.assert_called_once()
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs["customer"] == "cus_test123"
        assert call_kwargs["mode"] == "subscription"


class TestWebhookSubscriptionCreated:
    """Tests for webhook handling: subscription created."""

    @patch("app.services.subscription.stripe")
    def test_webhook_subscription_created(self, mock_stripe, svc):
        """checkout.session.completed should activate the user's tier."""
        mock_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"user_id": "user-456", "tier": "pro"},
                    "subscription": "sub_abc123",
                    "customer": "cus_def456",
                }
            },
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        # Stub internal methods
        svc._update_user_tier = MagicMock()
        svc._store_subscription = MagicMock()
        svc._get_user_email = MagicMock(return_value=None)

        result = svc.handle_webhook(b"payload", "sig_header")
        assert result["status"] == "activated"
        assert result["tier"] == "pro"
        svc._update_user_tier.assert_called_once_with("user-456", PlanTier.PRO)


class TestWebhookSubscriptionCancelled:
    """Tests for webhook handling: subscription deleted."""

    @patch("app.services.subscription.stripe")
    def test_webhook_subscription_cancelled(self, mock_stripe, svc):
        """customer.subscription.deleted should downgrade user to free."""
        mock_event = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "metadata": {"user_id": "user-789"},
                    "status": "canceled",
                }
            },
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        svc._update_user_tier = MagicMock()

        result = svc.handle_webhook(b"payload", "sig_header")
        assert result["status"] == "cancelled"
        svc._update_user_tier.assert_called_once_with("user-789", PlanTier.FREE)
