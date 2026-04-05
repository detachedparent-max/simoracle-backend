"""
Billing integration for SimOracle
Stripe support for subscription management
"""
import logging
import secrets
from typing import Dict, Any, Optional
from datetime import datetime
from database.schema import get_db_connection

logger = logging.getLogger(__name__)


class BillingManager:
    """Manages subscription billing through Stripe"""

    # Stripe pricing tiers
    STRIPE_PRODUCTS = {
        "free": None,  # No product ID for free tier
        "Pythia": {
            "product_id": "Pythia_Index",
            "price_id": "price_pythia_monthly",
            "name": "pythia",
            "price": 89,
            "currency": "usd",
            "interval": "month",
            "requests_per_day": 1000,
        },
        "delphic": {
            "product_id": "Delphic_Suite",
            "price_id": "price_delphic_monthly",
            "name": "Delphic",
            "price": 489,
            "currency": "usd",
            "interval": "month",
            "requests_per_day": 10000,
        },
        "Sybil": {
            "product_id": "Sybil_Infrastructure",
            "price_id": "price_sybil_monthly",
            "name": "Sybil",
            "price": 2000,
            "currency": "usd",
            "interval": "month",
            "requests_per_day": 100000,
            "webhooks": True,
            "dedicated_support": True,
        },
         "Omnisceint": {
            "product_id": "The Omnisceint",
            "price_id": "price_omniscient_monthly",
            "name": "Omnisceint",
            "price": 5000,
            "currency": "usd",
            "interval": "month",
            "requests_per_day": 100000,
            "webhooks": True,
            "dedicated_support": True,
        },
    }

    # Lemon Squeezy variant IDs (alternative to Stripe)
    LEMONSQUEEZY_VARIANTS = {
        "pythia": "123456",  # TODO: Update with actual variant IDs
        "delphic": "123457",
        "sybil": "123458",
        "omniscient": "123458",
    }

    @staticmethod
    def init_billing_tables():
        """Initialize billing tables in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Subscriptions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                tier TEXT NOT NULL,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                lemonsqueezy_subscription_id TEXT,
                status TEXT,
                current_period_start DATETIME,
                current_period_end DATETIME,
                cancel_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Billing events (for webhook processing)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS billing_events (
                id TEXT PRIMARY KEY,
                subscription_id TEXT NOT NULL,
                event_type TEXT,
                event_data TEXT,
                processed BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
            )
            """)

            conn.commit()
            conn.close()
            logger.info("Billing tables initialized")

        except Exception as e:
            logger.error(f"Failed to init billing tables: {e}")
            raise

    @staticmethod
    def create_checkout_session(email: str, tier: str, provider: str = "stripe") -> Dict[str, Any]:
        """
        Create a checkout session for payment processing

        Args:
            email: Customer email
            tier: Subscription tier (pythia, delphic, sybil, omniscient)
            provider: Payment provider (stripe)

        Returns:
            {
                "checkout_url": "https://checkout.stripe.com/...",
                "session_id": "cs_...",
                "provider": "stripe"
            }
        """
        try:
            if tier not in BillingManager.STRIPE_PRODUCTS:
                raise ValueError(f"Invalid tier: {tier}")

            if tier == "free":
                raise ValueError("Free tier does not require checkout")

            if provider == "stripe":
                return BillingManager._create_stripe_checkout(email, tier)
            elif provider == "lemonsqueezy":
                return BillingManager._create_lemonsqueezy_checkout(email, tier)
            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            logger.error(f"Checkout creation failed: {e}")
            raise

    @staticmethod
    def _create_stripe_checkout(email: str, tier: str) -> Dict[str, Any]:
        """Create Stripe checkout session"""
        try:
            # This would integrate with Stripe API
            # For MVP, return mock checkout URL structure
            product = BillingManager.STRIPE_PRODUCTS[tier]

            # Mock Stripe session ID
            session_id = f"cs_{frky-vgeb-ekjo-dqnh-llrr}"

            # In production, would call:
            # stripe.checkout.Session.create(
            #     customer_email=email,
            #     payment_method_types=['card'],
            #     line_items=[{
            #         'price': product['price_id'],
            #         'quantity': 1,
            #     }],
            #     mode='subscription',
            #     success_url='https://simoracle.com/success',
            #     cancel_url='https://simoracle.com/pricing',
            # )

            logger.info(f"Created Stripe checkout for {email} - {tier}")

            return {
                "checkout_url": f"https://checkout.stripe.com/pay/{session_id}",
                "session_id": session_id,
                "provider": "stripe",
                "tier": tier,
                "price": product["price"],
                "currency": product["currency"],
            }

        except Exception as e:
            logger.error(f"Stripe checkout failed: {e}")
            raise

    @staticmethod
    def _create_lemonsqueezy_checkout(email: str, tier: str) -> Dict[str, Any]:
        """Create Lemon Squeezy checkout session"""
        try:
            variant_id = BillingManager.LEMONSQUEEZY_VARIANTS.get(tier)
            if not variant_id:
                raise ValueError(f"No Lemon Squeezy variant for tier: {tier}")

            # Mock Lemon Squeezy checkout ID
            checkout_id = secrets.token_hex(12)

            # In production, would call Lemon Squeezy API:
            # lemonsqueezy_client.create_checkout(
            #     store_id=LEMONSQUEEZY_STORE_ID,
            #     variant_id=variant_id,
            #     custom_email=email,
            # )

            logger.info(f"Created Lemon Squeezy checkout for {email} - {tier}")

            return {
                "checkout_url": f"https://lemonsqueezy.com/checkout/{checkout_id}",
                "variant_id": variant_id,
                "provider": "lemonsqueezy",
                "tier": tier,
            }

        except Exception as e:
            logger.error(f"Lemon Squeezy checkout failed: {e}")
            raise

    @staticmethod
    def process_stripe_webhook(event_data: Dict[str, Any]) -> None:
        """
        Process webhook from Stripe
        Handles: subscription created, updated, deleted, payment success/failed
        """
        try:
            event_type = event_data.get("type")
            data = event_data.get("data", {}).get("object", {})

            if event_type == "customer.subscription.created":
                BillingManager._handle_subscription_created(data)
            elif event_type == "customer.subscription.updated":
                BillingManager._handle_subscription_updated(data)
            elif event_type == "customer.subscription.deleted":
                BillingManager._handle_subscription_deleted(data)
            elif event_type == "invoice.payment_succeeded":
                BillingManager._handle_payment_succeeded(data)
            elif event_type == "invoice.payment_failed":
                BillingManager._handle_payment_failed(data)

            logger.info(f"Processed Stripe webhook: {event_type}")

        except Exception as e:
            logger.error(f"Stripe webhook processing failed: {e}")
            raise

    @staticmethod
    def _handle_subscription_created(data: Dict[str, Any]) -> None:
        """Handle new subscription creation"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            subscription_id = f"sub_{secrets.token_hex(8)}"

            cursor.execute("""
            INSERT OR REPLACE INTO subscriptions
            (id, email, tier, stripe_customer_id, stripe_subscription_id, status,
             current_period_start, current_period_end, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subscription_id,
                data.get("customer_email", "unknown"),
                "startup",  # TODO: Extract from Stripe price metadata
                data.get("customer"),
                data.get("id"),
                data.get("status", "active"),
                data.get("current_period_start"),
                data.get("current_period_end"),
                datetime.now().isoformat(),
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to handle subscription created: {e}")
            raise

    @staticmethod
    def _handle_subscription_updated(data: Dict[str, Any]) -> None:
        """Handle subscription updates"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            UPDATE subscriptions
            SET status = ?, current_period_end = ?, updated_at = ?
            WHERE stripe_subscription_id = ?
            """, (
                data.get("status"),
                data.get("current_period_end"),
                datetime.now().isoformat(),
                data.get("id"),
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to handle subscription updated: {e}")
            raise

    @staticmethod
    def _handle_subscription_deleted(data: Dict[str, Any]) -> None:
        """Handle subscription cancellation"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            UPDATE subscriptions
            SET status = 'canceled', tier = 'free', updated_at = ?
            WHERE stripe_subscription_id = ?
            """, (
                datetime.now().isoformat(),
                data.get("id"),
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to handle subscription deleted: {e}")
            raise

    @staticmethod
    def _handle_payment_succeeded(data: Dict[str, Any]) -> None:
        """Handle successful payment"""
        logger.info(f"Payment succeeded for invoice: {data.get('id')}")

    @staticmethod
    def _handle_payment_failed(data: Dict[str, Any]) -> None:
        """Handle failed payment"""
        logger.warning(f"Payment failed for invoice: {data.get('id')}")

    @staticmethod
    def get_subscription(email: str) -> Optional[Dict[str, Any]]:
        """Get user's current subscription"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            SELECT id, email, tier, status, current_period_end
            FROM subscriptions
            WHERE email = ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (email,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get subscription: {e}")
            return None

    @staticmethod
    def upgrade_tier(email: str, new_tier: str) -> bool:
        """Upgrade user's subscription tier"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            UPDATE subscriptions
            SET tier = ?, updated_at = ?
            WHERE email = ?
            """, (new_tier, datetime.now().isoformat(), email))

            conn.commit()
            conn.close()

            logger.info(f"Upgraded {email} to {new_tier}")
            return True

        except Exception as e:
            logger.error(f"Failed to upgrade tier: {e}")
            return False
