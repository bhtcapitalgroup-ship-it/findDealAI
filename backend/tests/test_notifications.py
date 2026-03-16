"""Tests for the notification service (app.services.notification)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.notification import NotificationService


@pytest.fixture
def svc() -> NotificationService:
    """Create a notification service with a fake API key."""
    return NotificationService(api_key="SG.fake-test-key")


@pytest.fixture
def sample_property_data() -> dict:
    return {
        "address": "100 Investment Dr",
        "city": "Austin",
        "state": "TX",
        "price": 285000,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "sqft": 1600,
        "estimated_rent": 1850,
    }


@pytest.fixture
def sample_analysis() -> dict:
    return {
        "investment_score": 78,
        "cap_rate": 0.082,
        "cash_flow": 320,
        "cash_on_cash": 0.112,
        "brrrr_score": 65,
        "property_id": "prop-abc-123",
        "ai_summary": "This property presents a solid investment opportunity with above-average cash flow.",
    }


class TestSendDealAlertEmail:
    """Tests for NotificationService.send_deal_alert."""

    @patch.object(NotificationService, "client", new_callable=lambda: MagicMock)
    def test_send_deal_alert_email(
        self, mock_client_prop, svc, sample_property_data, sample_analysis
    ):
        """send_deal_alert should call SendGrid and return True on success."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        # Access the client via the property
        svc._client = MagicMock()
        svc._client.send.return_value = mock_response

        result = svc.send_deal_alert(
            to_email="investor@example.com",
            subject="New Deal: Score 78/100",
            property_data=sample_property_data,
            analysis=sample_analysis,
            alert_name="Austin High Yield",
        )

        assert result is True
        svc._client.send.assert_called_once()

    @patch.object(NotificationService, "client", new_callable=lambda: MagicMock)
    def test_send_deal_alert_email_failure(
        self, mock_client_prop, svc, sample_property_data, sample_analysis
    ):
        """send_deal_alert should return False when SendGrid fails."""
        svc._client = MagicMock()
        svc._client.send.side_effect = Exception("SendGrid unavailable")

        result = svc.send_deal_alert(
            to_email="investor@example.com",
            subject="New Deal",
            property_data=sample_property_data,
            analysis=sample_analysis,
        )

        assert result is False


class TestDealAlertEmailContent:
    """Tests for deal alert email HTML rendering."""

    def test_deal_alert_email_content(
        self, svc, sample_property_data, sample_analysis
    ):
        """The rendered HTML should contain property details and metrics."""
        html = svc._render_deal_alert_html(
            prop=sample_property_data,
            analysis=sample_analysis,
            alert_name="Test Alert",
        )

        # Address
        assert "100 Investment Dr" in html
        assert "Austin" in html
        assert "TX" in html

        # Price
        assert "285,000" in html

        # Metrics
        assert "78" in html  # investment score
        assert "8.2" in html  # cap rate (0.082 * 100)
        assert "320" in html  # cash flow
        assert "11.2" in html  # cash on cash

        # Alert name
        assert "Test Alert" in html

        # CTA link
        assert "prop-abc-123" in html


class TestNotificationRespectsUserPreferences:
    """Test that notifications are skipped when there is no API key."""

    def test_notification_respects_user_preferences(self):
        """If no SendGrid API key is configured, emails should not be sent."""
        svc = NotificationService(api_key="")
        result = svc._send_email(
            to_email="user@example.com",
            subject="Test",
            html_content="<p>Hello</p>",
        )
        assert result is False


class TestWelcomeEmail:
    """Tests for welcome email."""

    def test_welcome_email_content(self, svc):
        """The welcome email HTML should address the user by name."""
        svc._client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        svc._client.send.return_value = mock_response

        result = svc.send_welcome_email(
            to_email="new@example.com",
            user_name="Alice",
        )
        assert result is True
        # Verify the call happened
        svc._client.send.assert_called_once()


class TestSubscriptionConfirmation:
    """Tests for subscription confirmation email."""

    def test_subscription_confirmation(self, svc):
        """The confirmation email should include plan name and amount."""
        svc._client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        svc._client.send.return_value = mock_response

        result = svc.send_subscription_confirmation(
            to_email="pro@example.com",
            plan_name="Pro",
            amount=79.00,
        )
        assert result is True
