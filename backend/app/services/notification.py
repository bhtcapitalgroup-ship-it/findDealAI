"""
RealDeal AI - Notification Service

Handles email alerts via SendGrid and push notifications for deal alerts,
market updates, and account notifications.
"""

import logging
import os
from typing import Any, Optional

import sendgrid
from sendgrid.helpers.mail import Content, Email, Mail, To

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("NOTIFICATION_FROM_EMAIL", "alerts@realdeal-ai.com")
FROM_NAME = os.getenv("NOTIFICATION_FROM_NAME", "RealDeal AI")
APP_URL = os.getenv("APP_URL", "https://app.realdeal-ai.com")


class NotificationService:
    """Send email and push notifications to users."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or SENDGRID_API_KEY
        self._client: Optional[sendgrid.SendGridAPIClient] = None

    @property
    def client(self) -> sendgrid.SendGridAPIClient:
        if self._client is None:
            self._client = sendgrid.SendGridAPIClient(api_key=self._api_key)
        return self._client

    # ------------------------------------------------------------------
    # Deal Alert Email
    # ------------------------------------------------------------------

    def send_deal_alert(
        self,
        to_email: str,
        subject: str,
        property_data: dict[str, Any],
        analysis: dict[str, Any],
        alert_name: str = "Deal Alert",
    ) -> bool:
        """
        Send a deal alert email with property summary and analysis.

        Returns True on success, False on failure.
        """
        html = self._render_deal_alert_html(property_data, analysis, alert_name)

        return self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html,
        )

    # ------------------------------------------------------------------
    # Market Report Email
    # ------------------------------------------------------------------

    def send_market_report(
        self,
        to_email: str,
        market_name: str,
        report_html: str,
        stats: dict[str, Any],
    ) -> bool:
        """Send a weekly market report email."""
        html = self._render_market_report_html(market_name, report_html, stats)

        return self._send_email(
            to_email=to_email,
            subject=f"RealDeal AI Weekly Report: {market_name}",
            html_content=html,
        )

    # ------------------------------------------------------------------
    # Account Notifications
    # ------------------------------------------------------------------

    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email to new users."""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a56db; padding: 24px; text-align: center;">
                <h1 style="color: white; margin: 0;">Welcome to RealDeal AI</h1>
            </div>
            <div style="padding: 24px; background: #ffffff;">
                <p>Hi {user_name},</p>
                <p>Welcome to RealDeal AI! We're excited to help you find your next
                great real estate investment deal.</p>
                <h3>Getting Started:</h3>
                <ol>
                    <li><strong>Add your target markets</strong> - Tell us which cities you're interested in</li>
                    <li><strong>Set up deal alerts</strong> - Get notified when properties match your criteria</li>
                    <li><strong>Browse the deal feed</strong> - See AI-scored properties updated daily</li>
                </ol>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{APP_URL}/dashboard" style="background: #1a56db; color: white;
                    padding: 12px 24px; text-decoration: none; border-radius: 6px;
                    font-weight: bold;">Go to Dashboard</a>
                </div>
            </div>
            <div style="padding: 16px; background: #f3f4f6; text-align: center;
            font-size: 12px; color: #6b7280;">
                <p>&copy; 2026 RealDeal AI. All rights reserved.</p>
            </div>
        </div>
        """
        return self._send_email(
            to_email=to_email,
            subject="Welcome to RealDeal AI - Let's find your next deal!",
            html_content=html,
        )

    def send_subscription_confirmation(
        self, to_email: str, plan_name: str, amount: float
    ) -> bool:
        """Send subscription confirmation email."""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a56db; padding: 24px; text-align: center;">
                <h1 style="color: white; margin: 0;">Subscription Confirmed</h1>
            </div>
            <div style="padding: 24px; background: #ffffff;">
                <p>Your <strong>{plan_name}</strong> subscription is now active.</p>
                <div style="background: #f0fdf4; border: 1px solid #86efac; padding: 16px;
                border-radius: 8px; margin: 16px 0;">
                    <p style="margin: 0;"><strong>Plan:</strong> {plan_name}</p>
                    <p style="margin: 4px 0 0;"><strong>Amount:</strong> ${amount:.2f}/month</p>
                </div>
                <p>You now have access to all {plan_name} features. Happy investing!</p>
            </div>
        </div>
        """
        return self._send_email(
            to_email=to_email,
            subject=f"RealDeal AI - {plan_name} Subscription Confirmed",
            html_content=html,
        )

    # ------------------------------------------------------------------
    # Push Notifications (placeholder for Firebase / OneSignal)
    # ------------------------------------------------------------------

    def send_push_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
    ) -> bool:
        """
        Send a push notification via Firebase Cloud Messaging.

        In production, this would integrate with FCM or OneSignal.
        """
        try:
            # Load user's push token from database
            push_token = self._get_push_token(user_id)
            if not push_token:
                logger.debug("No push token for user %s", user_id)
                return False

            # Firebase / OneSignal integration would go here
            payload = {
                "to": push_token,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "data": data or {},
            }

            logger.info(
                "Push notification sent to user %s: %s", user_id, title
            )
            return True

        except Exception as exc:
            logger.error("Push notification failed for user %s: %s", user_id, exc)
            return False

    def send_deal_push(
        self,
        user_id: str,
        property_address: str,
        investment_score: int,
        property_id: str,
    ) -> bool:
        """Send a push notification for a deal alert match."""
        return self.send_push_notification(
            user_id=user_id,
            title=f"New Deal: Score {investment_score}/100",
            body=f"{property_address} just hit your alert criteria!",
            data={
                "type": "deal_alert",
                "property_id": property_id,
                "screen": "property_detail",
            },
        )

    # ------------------------------------------------------------------
    # Email rendering
    # ------------------------------------------------------------------

    def _render_deal_alert_html(
        self,
        prop: dict[str, Any],
        analysis: dict[str, Any],
        alert_name: str,
    ) -> str:
        score = analysis.get("investment_score", 0)
        score_color = "#16a34a" if score >= 70 else "#ca8a04" if score >= 50 else "#dc2626"

        cap_rate = analysis.get("cap_rate", 0)
        cash_flow = analysis.get("cash_flow", 0)
        cash_on_cash = analysis.get("cash_on_cash", 0)
        brrrr = analysis.get("brrrr_score", 0)

        address = prop.get("address", "")
        city = prop.get("city", "")
        state = prop.get("state", "")
        price = prop.get("price", 0)
        beds = prop.get("bedrooms", 0)
        baths = prop.get("bathrooms", 0)
        sqft = prop.get("sqft", 0)
        rent = prop.get("estimated_rent", 0)

        property_id = analysis.get("property_id", "")
        detail_url = f"{APP_URL}/properties/{property_id}"

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a56db; padding: 24px; text-align: center;">
                <h1 style="color: white; margin: 0;">Deal Alert: {alert_name}</h1>
            </div>
            <div style="padding: 24px; background: #ffffff;">
                <!-- Score badge -->
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="display: inline-block; background: {score_color}; color: white;
                    font-size: 36px; font-weight: bold; padding: 16px 24px; border-radius: 12px;">
                        {score}<span style="font-size: 16px;">/100</span>
                    </div>
                </div>

                <!-- Property info -->
                <h2 style="margin: 0 0 4px;">{address}</h2>
                <p style="color: #6b7280; margin: 0 0 16px;">{city}, {state}</p>

                <div style="display: flex; gap: 16px; margin-bottom: 16px;">
                    <div style="background: #f3f4f6; padding: 12px; border-radius: 8px; flex: 1; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold;">${price:,.0f}</div>
                        <div style="font-size: 12px; color: #6b7280;">List Price</div>
                    </div>
                    <div style="background: #f3f4f6; padding: 12px; border-radius: 8px; flex: 1; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold;">${rent:,.0f}</div>
                        <div style="font-size: 12px; color: #6b7280;">Est. Rent/mo</div>
                    </div>
                </div>

                <p style="color: #374151;">{beds} bed | {baths} bath | {sqft:,} sqft</p>

                <!-- Key metrics -->
                <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                    <tr style="border-bottom: 1px solid #e5e7eb;">
                        <td style="padding: 8px 0; color: #6b7280;">Cap Rate</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: bold;">{cap_rate * 100:.1f}%</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e5e7eb;">
                        <td style="padding: 8px 0; color: #6b7280;">Monthly Cash Flow</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: bold;
                        color: {'#16a34a' if cash_flow > 0 else '#dc2626'};">${cash_flow:,.0f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e5e7eb;">
                        <td style="padding: 8px 0; color: #6b7280;">Cash-on-Cash</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: bold;">{cash_on_cash * 100:.1f}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6b7280;">BRRRR Score</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: bold;">{brrrr:.0f}/100</td>
                    </tr>
                </table>

                <!-- AI Summary -->
                {"<div style='background: #eff6ff; border-left: 4px solid #1a56db; padding: 12px; margin: 16px 0; border-radius: 0 8px 8px 0;'><strong>AI Analysis:</strong> " + analysis.get('ai_summary', '')[:300] + "...</div>" if analysis.get('ai_summary') else ""}

                <!-- CTA -->
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{detail_url}" style="background: #1a56db; color: white;
                    padding: 14px 28px; text-decoration: none; border-radius: 8px;
                    font-weight: bold; font-size: 16px;">View Full Analysis</a>
                </div>
            </div>

            <div style="padding: 16px; background: #f3f4f6; text-align: center;
            font-size: 12px; color: #6b7280;">
                <p>You received this because of your "{alert_name}" alert.</p>
                <a href="{APP_URL}/settings/alerts" style="color: #1a56db;">Manage Alerts</a>
                <p>&copy; 2026 RealDeal AI</p>
            </div>
        </div>
        """

    def _render_market_report_html(
        self,
        market_name: str,
        report_content: str,
        stats: dict[str, Any],
    ) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a56db; padding: 24px; text-align: center;">
                <h1 style="color: white; margin: 0;">Weekly Market Report</h1>
                <p style="color: #bfdbfe; margin: 4px 0 0;">{market_name}</p>
            </div>
            <div style="padding: 24px; background: #ffffff;">
                <div style="display: flex; gap: 12px; margin-bottom: 20px;">
                    <div style="flex: 1; background: #f3f4f6; padding: 12px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 18px; font-weight: bold;">${stats.get('median_home_price', 0):,.0f}</div>
                        <div style="font-size: 11px; color: #6b7280;">Median Price</div>
                    </div>
                    <div style="flex: 1; background: #f3f4f6; padding: 12px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 18px; font-weight: bold;">${stats.get('median_rent', 0):,.0f}</div>
                        <div style="font-size: 11px; color: #6b7280;">Median Rent</div>
                    </div>
                    <div style="flex: 1; background: #f3f4f6; padding: 12px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 18px; font-weight: bold;">{stats.get('active_listings', 0):,}</div>
                        <div style="font-size: 11px; color: #6b7280;">Listings</div>
                    </div>
                </div>
                <div style="line-height: 1.6;">{report_content}</div>
            </div>
            <div style="padding: 16px; background: #f3f4f6; text-align: center; font-size: 12px; color: #6b7280;">
                <a href="{APP_URL}/markets" style="color: #1a56db;">View All Markets</a>
                <p>&copy; 2026 RealDeal AI</p>
            </div>
        </div>
        """

    # ------------------------------------------------------------------
    # Core email sending
    # ------------------------------------------------------------------

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send an email via SendGrid."""
        if not self._api_key:
            logger.warning("SendGrid API key not configured; email not sent to %s", to_email)
            return False

        try:
            message = Mail(
                from_email=Email(FROM_EMAIL, FROM_NAME),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            response = self.client.send(message)

            if response.status_code in (200, 201, 202):
                logger.info("Email sent to %s: %s (status %d)", to_email, subject, response.status_code)
                return True
            else:
                logger.error(
                    "SendGrid returned status %d for %s: %s",
                    response.status_code,
                    to_email,
                    response.body,
                )
                return False

        except Exception as exc:
            logger.error("Email send failed to %s: %s", to_email, exc)
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_push_token(user_id: str) -> Optional[str]:
        """Look up a user's push notification token from database."""
        # In production: query user_devices table
        return None
