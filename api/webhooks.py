"""
Webhook system for SimOracle
Real-time prediction push notifications to customer endpoints
"""
import logging
import secrets
import hmac
import hashlib
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from database.schema import get_db_connection

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages webhook subscriptions and delivery"""

    WEBHOOK_TIMEOUT = 30  # seconds
    WEBHOOK_RETRY_ATTEMPTS = 3
    WEBHOOK_RETRY_BACKOFF = [5, 30, 300]  # seconds: 5s, 30s, 5m

    @staticmethod
    def init_webhook_tables():
        """Initialize webhook tables in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Webhook subscriptions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_subscriptions (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                url TEXT NOT NULL,
                events TEXT NOT NULL,
                secret TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_test_at DATETIME
            )
            """)

            # Webhook delivery history
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id TEXT PRIMARY KEY,
                webhook_id TEXT NOT NULL,
                event_type TEXT,
                event_id TEXT,
                payload TEXT,
                http_status INTEGER,
                response_body TEXT,
                attempt INTEGER DEFAULT 1,
                next_retry_at DATETIME,
                delivered_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (webhook_id) REFERENCES webhook_subscriptions(id)
            )
            """)

            conn.commit()
            conn.close()
            logger.info("Webhook tables initialized")

        except Exception as e:
            logger.error(f"Failed to init webhook tables: {e}")
            raise

    @staticmethod
    def subscribe(
        email: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new webhook subscription

        Args:
            email: Customer email
            url: Webhook endpoint URL
            events: List of events to subscribe to (prediction.created, prediction.resolved)
            secret: Optional secret for HMAC signing (auto-generated if not provided)

        Returns:
            {
                "webhook_id": "wh_xyz",
                "url": "https://customer.com/webhooks",
                "events": ["prediction.created"],
                "status": "active"
            }
        """
        try:
            webhook_id = f"wh_{secrets.token_hex(12)}"
            webhook_secret = secret or secrets.token_urlsafe(32)

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO webhook_subscriptions
            (id, email, url, events, secret, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                webhook_id,
                email,
                url,
                json.dumps(events),
                webhook_secret,
                "active",
            ))

            conn.commit()
            conn.close()

            logger.info(f"Created webhook subscription {webhook_id} for {email}")

            return {
                "webhook_id": webhook_id,
                "url": url,
                "events": events,
                "status": "active",
                "secret": webhook_secret,  # Only return once
            }

        except Exception as e:
            logger.error(f"Failed to create webhook subscription: {e}")
            raise

    @staticmethod
    def list_subscriptions(email: str) -> List[Dict[str, Any]]:
        """List all webhook subscriptions for a customer"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            SELECT id, url, events, status, created_at, last_test_at
            FROM webhook_subscriptions
            WHERE email = ?
            ORDER BY created_at DESC
            """, (email,))

            results = cursor.fetchall()
            conn.close()

            return [
                {
                    "webhook_id": row[0],
                    "url": row[1],
                    "events": json.loads(row[2]),
                    "status": row[3],
                    "created_at": row[4],
                    "last_test_at": row[5],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            return []

    @staticmethod
    def delete_subscription(webhook_id: str, email: str) -> bool:
        """Delete a webhook subscription"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            DELETE FROM webhook_subscriptions
            WHERE id = ? AND email = ?
            """, (webhook_id, email))

            conn.commit()
            conn.close()

            logger.info(f"Deleted webhook {webhook_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False

    @staticmethod
    async def dispatch_event(
        event_type: str,
        event_data: Dict[str, Any],
        affected_email: Optional[str] = None,
    ) -> None:
        """
        Dispatch event to all subscribed webhooks
        Handles retries with exponential backoff

        Args:
            event_type: Event type (prediction.created, prediction.resolved)
            event_data: Event payload
            affected_email: Optional email to filter subscriptions
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get all active subscriptions that care about this event
            if affected_email:
                cursor.execute("""
                SELECT id, url, secret, events
                FROM webhook_subscriptions
                WHERE status = 'active' AND email = ?
                """, (affected_email,))
            else:
                cursor.execute("""
                SELECT id, url, secret, events
                FROM webhook_subscriptions
                WHERE status = 'active'
                """)

            webhooks = cursor.fetchall()
            conn.close()

            # Filter by event type and dispatch
            tasks = []
            for webhook_id, url, secret, events_json in webhooks:
                events = json.loads(events_json)
                if event_type in events:
                    tasks.append(
                        WebhookManager._deliver_webhook(
                            webhook_id, url, secret, event_type, event_data
                        )
                    )

            if tasks:
                import asyncio
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Failed to dispatch event: {e}")

    @staticmethod
    async def _deliver_webhook(
        webhook_id: str,
        url: str,
        secret: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        """
        Deliver a single webhook with retry logic
        """
        event_id = f"evt_{secrets.token_hex(8)}"
        payload = {
            "id": event_id,
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": event_data,
        }

        for attempt in range(WebhookManager.WEBHOOK_RETRY_ATTEMPTS):
            try:
                # Create HMAC signature
                payload_json = json.dumps(payload)
                signature = hmac.new(
                    secret.encode(),
                    payload_json.encode(),
                    hashlib.sha256,
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-SimOracle-Event": event_type,
                    "X-SimOracle-Signature": f"sha256={signature}",
                    "X-SimOracle-Delivery": event_id,
                }

                async with httpx.AsyncClient(timeout=WebhookManager.WEBHOOK_TIMEOUT) as client:
                    response = await client.post(url, content=payload_json, headers=headers)

                    # Log delivery
                    WebhookManager._log_delivery(
                        webhook_id,
                        event_id,
                        event_type,
                        response.status_code,
                        response.text,
                        attempt + 1,
                    )

                    if response.status_code in [200, 201, 204]:
                        logger.info(f"Webhook delivered: {webhook_id} -> {event_type}")
                        return

                    # Retry on 5xx or connection errors
                    if response.status_code >= 500 or attempt < WebhookManager.WEBHOOK_RETRY_ATTEMPTS - 1:
                        continue

                    logger.warning(
                        f"Webhook delivery failed: {webhook_id} - status {response.status_code}"
                    )
                    return

            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(f"Webhook delivery error (attempt {attempt + 1}): {e}")

                if attempt < WebhookManager.WEBHOOK_RETRY_ATTEMPTS - 1:
                    # Schedule retry
                    retry_delay = WebhookManager.WEBHOOK_RETRY_BACKOFF[attempt]
                    next_retry = (
                        datetime.utcnow() + timedelta(seconds=retry_delay)
                    ).isoformat()

                    # Update database with next retry time
                    WebhookManager._log_delivery(
                        webhook_id,
                        event_id,
                        event_type,
                        0,
                        str(e),
                        attempt + 1,
                        next_retry,
                    )

                    import asyncio
                    await asyncio.sleep(retry_delay)
                    continue

                logger.error(f"Webhook delivery failed after {WebhookManager.WEBHOOK_RETRY_ATTEMPTS} attempts")
                return

    @staticmethod
    def _log_delivery(
        webhook_id: str,
        event_id: str,
        event_type: str,
        http_status: int,
        response_body: str,
        attempt: int,
        next_retry_at: Optional[str] = None,
    ) -> None:
        """Log webhook delivery attempt"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            delivery_id = f"del_{secrets.token_hex(8)}"

            cursor.execute("""
            INSERT INTO webhook_deliveries
            (id, webhook_id, event_type, event_id, http_status, response_body, attempt, next_retry_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                delivery_id,
                webhook_id,
                event_type,
                event_id,
                http_status,
                response_body[:500],  # Truncate response
                attempt,
                next_retry_at,
            ))

            if http_status in [200, 201, 204]:
                cursor.execute("""
                UPDATE webhook_deliveries
                SET delivered_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (delivery_id,))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.warning(f"Failed to log webhook delivery: {e}")

    @staticmethod
    async def test_webhook(webhook_id: str, secret: str) -> Dict[str, Any]:
        """
        Send a test event to a webhook
        Used to verify webhook endpoint is working
        """
        try:
            test_payload = {
                "id": "evt_test",
                "type": "test",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "message": "This is a test webhook from SimOracle",
                },
            }

            # Get webhook URL
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT url FROM webhook_subscriptions WHERE id = ?", (webhook_id,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                raise ValueError("Webhook not found")

            url = result[0]

            # Create signature and send
            payload_json = json.dumps(test_payload)
            signature = hmac.new(
                secret.encode(),
                payload_json.encode(),
                hashlib.sha256,
            ).hexdigest()

            headers = {
                "Content-Type": "application/json",
                "X-SimOracle-Event": "test",
                "X-SimOracle-Signature": f"sha256={signature}",
            }

            async with httpx.AsyncClient(timeout=WebhookManager.WEBHOOK_TIMEOUT) as client:
                response = await client.post(url, content=payload_json, headers=headers)

                return {
                    "status": "success" if response.status_code < 400 else "failed",
                    "http_status": response.status_code,
                    "response": response.text[:200],
                }

        except Exception as e:
            logger.error(f"Webhook test failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
