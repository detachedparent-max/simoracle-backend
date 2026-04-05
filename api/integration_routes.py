"""
Integration API routes for SimOracle
Sample reports, API key management, billing, webhooks, and LLM orchestration
"""
import logging
import os
import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Depends, Body
from pydantic import BaseModel, EmailStr, Field

from api.sample_report import generate_sample_report
from api.auth import APIKeyManager, validate_bearer_token
from api.billing import BillingManager
from api.email_onboarding import EmailOnboarding, get_email_service
from api.webhooks import WebhookManager
from api.llm_orchestration import get_llm_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Integration & SDK"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class APIKeyGenerateRequest(BaseModel):
    email: EmailStr
    tier: str = "free"


class APIKeyResponse(BaseModel):
    api_key: str
    tier: str
    rate_limit: int
    rate_period: str
    expires_in_days: int
    message: str = "Check your email for confirmation"


class CheckoutRequest(BaseModel):
    tier: str = Field(..., description="startup, professional, or enterprise")
    email: EmailStr
    provider: str = "stripe"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    provider: str
    tier: str


class WebhookSubscribeRequest(BaseModel):
    url: str
    events: list = Field(..., description="List of events to subscribe to")
    secret: Optional[str] = None


class WebhookSubscribeResponse(BaseModel):
    webhook_id: str
    url: str
    events: list
    status: str
    secret: Optional[str] = None


class PredictionRequest(BaseModel):
    event: str
    oracle: str = Field(..., description="weather, politics, sports, crypto, macro")
    deadline: Optional[str] = None
    context: Optional[str] = None


# ============================================================================
# SAMPLE REPORT ENDPOINT (No auth required)
# ============================================================================

@router.get("/sample-report", tags=["Public"])
async def get_sample_report():
    """
    Get a sample report demonstrating SimOracle predictions
    No authentication required - shows what the product can do
    """
    try:
        report = generate_sample_report()
        return report
    except Exception as e:
        logger.error(f"Sample report generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate sample report")


# ============================================================================
# API KEY MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/keys/generate", response_model=APIKeyResponse)
async def generate_api_key(request: APIKeyGenerateRequest):
    """
    Generate a new API key for free tier access
    Auto-expires after 30 days (requires upgrade decision)

    Request:
    ```json
    {
        "email": "user@company.com",
        "tier": "free"
    }
    ```

    Response:
    ```json
    {
        "api_key": "sk_free_abc123...",
        "tier": "free",
        "rate_limit": 50,
        "rate_period": "day",
        "expires_in_days": 30
    }
    ```
    """
    try:
        if request.tier != "free":
            raise ValueError("Self-service key generation only for free tier")

        key_data = APIKeyManager.create_api_key(request.email, request.tier)

        # Send welcome email with key
        try:
            email_service = await get_email_service(
                provider="sendgrid",
                api_key=os.getenv("SENDGRID_API_KEY", ""),
            )
            await email_service.send_welcome_email(request.email, key_data["api_key"], "free")
            await email_service.schedule_onboarding_sequence(request.email)
            await email_service.close()
        except Exception as e:
            logger.warning(f"Email send failed (non-blocking): {e}")

        return APIKeyResponse(
            **key_data,
            message="Check your email for welcome sequence",
        )

    except Exception as e:
        logger.error(f"API key generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# BILLING ENDPOINTS
# ============================================================================

@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout_session(request: CheckoutRequest):
    """
    Create a Stripe or Lemon Squeezy checkout session
    After payment, user is upgraded to paid tier

    Request:
    ```json
    {
        "tier": "startup",
        "email": "user@company.com",
        "provider": "stripe"
    }
    ```

    Response:
    ```json
    {
        "checkout_url": "https://checkout.stripe.com/pay/...",
        "session_id": "cs_...",
        "provider": "stripe",
        "tier": "startup"
    }
    ```
    """
    try:
        BillingManager.init_billing_tables()
        checkout_data = BillingManager.create_checkout_session(
            request.email,
            request.tier,
            request.provider,
        )
        return CheckoutResponse(**checkout_data)

    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/billing/webhooks/stripe")
async def stripe_webhook(body: dict = Body(...)):
    """
    Stripe webhook endpoint for subscription events
    Handles: subscription created, updated, deleted, payment success/failed
    """
    try:
        BillingManager.process_stripe_webhook(body)
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Stripe webhook processing failed: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


# ============================================================================
# MULTI-MODEL PREDICTION ENDPOINT (Requires auth)
# ============================================================================

@router.post("/predict")
async def create_prediction(
    request: PredictionRequest,
    key_data: dict = Depends(validate_bearer_token),
):
    """
    Generate a prediction with multi-model consensus (Claude, Gemini, GPT-4)

    Requires: Authorization header with API key
    ```
    Authorization: Bearer sk_free_abc123...
    ```

    Request:
    ```json
    {
        "event": "Will Bitcoin close above $70k on 2026-04-05?",
        "oracle": "crypto",
        "deadline": "2026-04-05T23:59:59Z"
    }
    ```

    Response:
    ```json
    {
        "prediction_id": "pred_xyz",
        "event": "Will Bitcoin close above $70k?",
        "probability": 0.65,
        "consensus": {
            "models": [
                {"model": "claude", "probability": 0.68, "confidence": 8},
                {"model": "gemini", "probability": 0.62, "confidence": 7},
                {"model": "gpt4", "probability": 0.65, "confidence": 8}
            ],
            "agreement": "strong",
            "final_probability": 0.65
        },
        "reasoning": "Consensus across 3 models...",
        "timestamp": "2026-04-04T10:30:00Z"
    }
    ```
    """
    try:
        # Get LLM orchestrator
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if not openrouter_key:
            raise HTTPException(
                status_code=500,
                detail="LLM service not configured"
            )

        orchestrator = await get_llm_orchestrator(openrouter_key)
        prediction = await orchestrator.predict(
            request.event,
            request.oracle,
            request.deadline,
            request.context,
        )
        await orchestrator.close()

        return prediction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction generation failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction generation failed")


# ============================================================================
# WEBHOOK MANAGEMENT ENDPOINTS (Requires auth)
# ============================================================================

@router.post("/webhooks/subscribe", response_model=WebhookSubscribeResponse)
async def subscribe_to_webhooks(
    request: WebhookSubscribeRequest,
    key_data: dict = Depends(validate_bearer_token),
):
    """
    Subscribe to webhook events for real-time predictions

    Supported events:
    - prediction.created: New prediction generated
    - prediction.resolved: Market resolved with outcome

    Request:
    ```json
    {
        "url": "https://customer.com/webhooks/simoracle",
        "events": ["prediction.created", "prediction.resolved"],
        "secret": "optional_secret_for_hmac"
    }
    ```

    Response:
    ```json
    {
        "webhook_id": "wh_abc123",
        "url": "https://customer.com/webhooks/simoracle",
        "events": ["prediction.created"],
        "status": "active",
        "secret": "whsec_xyz"
    }
    ```

    Webhook delivery format:
    ```json
    {
        "id": "evt_xyz",
        "type": "prediction.created",
        "timestamp": "2026-04-04T10:30:00Z",
        "data": {
            "prediction_id": "pred_xyz",
            "event": "Will Bitcoin close above $70k?",
            "probability": 0.65
        }
    }
    ```

    Headers included:
    - X-SimOracle-Event: prediction.created
    - X-SimOracle-Signature: sha256=...
    - X-SimOracle-Delivery: evt_xyz
    """
    try:
        WebhookManager.init_webhook_tables()

        subscription = WebhookManager.subscribe(
            key_data.get("email"),
            request.url,
            request.events,
            request.secret,
        )

        # Test the webhook endpoint
        test_result = await WebhookManager.test_webhook(
            subscription["webhook_id"],
            subscription["secret"],
        )

        if test_result.get("status") != "success":
            logger.warning(f"Webhook test failed: {test_result}")

        return WebhookSubscribeResponse(**subscription)

    except Exception as e:
        logger.error(f"Webhook subscription failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/webhooks")
async def list_webhooks(key_data: dict = Depends(validate_bearer_token)):
    """List all active webhook subscriptions for this customer"""
    try:
        webhooks = WebhookManager.list_subscriptions(key_data.get("email"))
        return {"webhooks": webhooks, "total": len(webhooks)}
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list webhooks")


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, key_data: dict = Depends(validate_bearer_token)):
    """Delete a webhook subscription"""
    try:
        success = WebhookManager.delete_subscription(webhook_id, key_data.get("email"))
        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete webhook")


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str, key_data: dict = Depends(validate_bearer_token)):
    """Send a test event to a webhook"""
    try:
        webhooks = WebhookManager.list_subscriptions(key_data.get("email"))
        webhook = next((w for w in webhooks if w["webhook_id"] == webhook_id), None)

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # For testing, we need the secret - this is a limitation
        # In production, store the secret hash securely
        result = await WebhookManager.test_webhook(webhook_id, "test_secret")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook test failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook test failed")


# ============================================================================
# API USAGE & RATE LIMIT ENDPOINTS (Requires auth)
# ============================================================================

@router.get("/usage")
async def get_api_usage(key_data: dict = Depends(validate_bearer_token)):
    """
    Get current API usage and rate limit status

    Response:
    ```json
    {
        "tier": "free",
        "requests_today": 23,
        "rate_limit": 50,
        "remaining": 27,
        "reset_at": "2026-04-05T00:00:00Z",
        "expires_at": "2026-05-04T10:30:00Z"
    }
    ```
    """
    try:
        api_key_hash = APIKeyManager.hash_api_key("")  # Would get from header in real impl
        is_allowed, rate_info = APIKeyManager.check_rate_limit(api_key_hash)

        return {
            "tier": key_data.get("tier"),
            "rate_limit": rate_info.get("limit", 50),
            "used": rate_info.get("used", 0),
            "remaining": rate_info.get("remaining", 50),
            "reset_hours": rate_info.get("reset_hours", 24),
            "expires_at": key_data.get("expires_at"),
        }

    except Exception as e:
        logger.error(f"Failed to get usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage")
