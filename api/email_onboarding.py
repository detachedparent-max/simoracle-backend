"""
Email onboarding workflow for SimOracle
Welcome series and API key delivery via SendGrid or Mailgun
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from database.schema import get_db_connection

logger = logging.getLogger(__name__)


class EmailOnboarding:
    """Manages multi-step email onboarding sequence"""

    SENDGRID_API_BASE = "https://api.sendgrid.com/v3"
    MAILGUN_API_BASE = "https://api.mailgun.net/v3"

    # Email sequence: (delay_days, subject, template_id)
    EMAIL_SEQUENCE = [
        (0, "Welcome to SimOracle - Your API Key Inside", "welcome_api_key"),
        (1, "Your First Prediction Report", "first_prediction"),
        (3, "API Quota & Usage Dashboard", "usage_dashboard"),
        (7, "Ready to Integrate? Institutional Trial", "institutional_trial"),
    ]

    def __init__(self, provider: str = "sendgrid", api_key: str = ""):
        """
        Initialize email service
        Args:
            provider: 'sendgrid' or 'mailgun'
            api_key: API key for the chosen provider
        """
        self.provider = provider
        self.api_key = api_key
        self.client = None

    async def get_client(self) -> httpx.AsyncClient:
        """Lazy-load async HTTP client"""
        if self.client is None:
            if self.provider == "sendgrid":
                base_url = self.SENDGRID_API_BASE
                headers = {"Authorization": f"Bearer {self.api_key}"}
            else:  # mailgun
                base_url = self.MAILGUN_API_BASE
                headers = {"Authorization": f"Basic {self.api_key}"}

            self.client = httpx.AsyncClient(
                base_url=base_url,
                headers=headers,
                timeout=30,
            )
        return self.client

    async def send_welcome_email(
        self,
        email: str,
        api_key: str,
        tier: str = "free",
    ) -> bool:
        """
        Send welcome email with API key

        Args:
            email: Recipient email
            api_key: Generated API key to include
            tier: Subscription tier (free, startup, professional, enterprise)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Log onboarding event
            self._log_onboarding_event(email, "welcome_email_sent", {"tier": tier})

            if self.provider == "sendgrid":
                return await self._send_sendgrid_welcome(email, api_key, tier)
            else:
                return await self._send_mailgun_welcome(email, api_key, tier)

        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return False

    async def _send_sendgrid_welcome(
        self,
        email: str,
        api_key: str,
        tier: str,
    ) -> bool:
        """Send via SendGrid"""
        try:
            client = await self.get_client()

            response = await client.post(
                "/mail/send",
                json={
                    "personalizations": [
                        {
                            "to": [{"email": email}],
                            "subject": "Welcome to SimOracle - Your API Key Inside",
                        }
                    ],
                    "from": {
                        "email": "api@simoracle.com",
                        "name": "SimOracle",
                    },
                    "content": [
                        {
                            "type": "text/html",
                            "value": self._render_welcome_template(api_key, tier),
                        }
                    ],
                    "reply_to": {
                        "email": "support@simoracle.com",
                    },
                },
            )

            response.raise_for_status()
            logger.info(f"Welcome email sent to {email} via SendGrid")
            return True

        except Exception as e:
            logger.error(f"SendGrid email failed: {e}")
            return False

    async def _send_mailgun_welcome(
        self,
        email: str,
        api_key: str,
        tier: str,
    ) -> bool:
        """Send via Mailgun"""
        try:
            client = await self.get_client()

            # Mailgun requires domain in URL path
            domain = "simoracle.com"
            response = await client.post(
                f"/{domain}/messages",
                data={
                    "from": "SimOracle <api@simoracle.com>",
                    "to": email,
                    "subject": "Welcome to SimOracle - Your API Key Inside",
                    "html": self._render_welcome_template(api_key, tier),
                    "reply-to": "support@simoracle.com",
                },
            )

            response.raise_for_status()
            logger.info(f"Welcome email sent to {email} via Mailgun")
            return True

        except Exception as e:
            logger.error(f"Mailgun email failed: {e}")
            return False

    def _render_welcome_template(self, api_key: str, tier: str) -> str:
        """Render HTML email template"""
        return f"""
        <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #0066cc;">Welcome to SimOracle</h1>

                    <p>You're now part of the institutional prediction engine trusted by traders and analysts.</p>

                    <h2>Your API Key</h2>
                    <p>Here's your API key for {tier.title()} tier (50 requests/day, 30-day trial):</p>

                    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace; word-break: break-all;">
                        {api_key}
                    </div>

                    <p style="color: #666; font-size: 12px;">
                        Keep this key safe. Never share it or commit it to version control.
                    </p>

                    <h2>Get Started in 3 Steps</h2>
                    <ol>
                        <li><strong>Generate a sample report:</strong>
                            <br/>
                            <code style="background: #f5f5f5; padding: 2px 5px; border-radius: 3px;">
                                curl https://api.simoracle.com/api/sample-report
                            </code>
                        </li>
                        <li><strong>Make your first API call:</strong>
                            <br/>
                            <code style="background: #f5f5f5; padding: 2px 5px; border-radius: 3px;">
                                curl -H "Authorization: Bearer {api_key[:20]}..." \\<br/>
                                https://api.simoracle.com/api/v1/predictions
                            </code>
                        </li>
                        <li><strong>Read the docs:</strong>
                            <br/>
                            <a href="https://simoracle.com/docs/api">API Documentation</a>
                        </li>
                    </ol>

                    <h2>Next Steps</h2>
                    <ul>
                        <li>Explore predictions across 5 oracles (weather, politics, sports, crypto, macro)</li>
                        <li>Subscribe to webhooks for real-time predictions</li>
                        <li>Upgrade to Professional tier for 10,000 requests/day</li>
                    </ul>

                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">

                    <p style="color: #666; font-size: 12px;">
                        Questions? Email support@simoracle.com or visit our docs at simoracle.com/docs
                    </p>

                    <p style="color: #999; font-size: 11px;">
                        SimOracle Inc. | San Francisco, CA
                    </p>
                </div>
            </body>
        </html>
        """

    async def schedule_onboarding_sequence(self, email: str) -> bool:
        """
        Schedule the full 7-day email sequence
        For MVP, this logs the schedule; in production would use job queue
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Create onboarding_schedule table if needed
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_schedule (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                sequence_index INTEGER,
                scheduled_for DATETIME,
                sent_at DATETIME,
                status TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Schedule all emails in sequence
            import secrets
            for delay_days, subject, template_id in self.EMAIL_SEQUENCE:
                scheduled_for = (datetime.now() + timedelta(days=delay_days)).isoformat()
                schedule_id = f"sched_{secrets.token_hex(8)}"

                cursor.execute("""
                INSERT INTO onboarding_schedule
                (id, email, sequence_index, scheduled_for, status)
                VALUES (?, ?, ?, ?, ?)
                """, (schedule_id, email, 0, scheduled_for, "pending"))

            conn.commit()
            conn.close()

            logger.info(f"Scheduled onboarding sequence for {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule onboarding: {e}")
            return False

    def _log_onboarding_event(
        self,
        email: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log onboarding event for analytics"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_events (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                event_type TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            import secrets
            import json
            cursor.execute("""
            INSERT INTO onboarding_events (id, email, event_type, metadata)
            VALUES (?, ?, ?, ?)
            """, (
                f"evt_{secrets.token_hex(8)}",
                email,
                event_type,
                json.dumps(metadata or {}),
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.warning(f"Failed to log onboarding event: {e}")

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()


async def get_email_service(provider: str = "sendgrid", api_key: str = "") -> EmailOnboarding:
    """Factory function to get email service instance"""
    return EmailOnboarding(provider, api_key)
