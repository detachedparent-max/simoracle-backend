# SimOracle API Documentation

## Overview

SimOracle is an institutional prediction engine with multi-model LLM consensus, real-time webhooks, and subscription billing integration. This API powers research, trading, and institutional workflows.

**Base URL:** `https://api.simoracle.com`  
**API Version:** v1  
**Status:** MVP (Launch Week)

---

## Quick Start

### 1. Get a Sample Report (No Auth)

See what SimOracle predicts without signing up:

```bash
curl https://api.simoracle.com/api/sample-report
```

Response:
```json
{
  "report_id": "sample_20260404_102030",
  "predictions": [
    {
      "event": "Will NOAA forecast rain in NYC on 2026-04-05?",
      "oracle": "weather",
      "probability": 0.72,
      "action": "BUY_YES",
      "reasoning": "70% chance of precipitation...",
      "catalysts": ["Low pressure system moving northeast"],
      "confidence": 8,
      "generated_at": "2026-04-04T10:30:00Z"
    }
  ],
  "report_generated_at": "2026-04-04T10:30:00Z",
  "disclaimer": "Predictions are for informational purposes..."
}
```

### 2. Generate an API Key (Free Tier)

```bash
curl -X POST https://api.simoracle.com/api/v1/keys/generate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@company.com",
    "tier": "free"
  }'
```

Response:
```json
{
  "api_key": "sk_free_abc123xyz...",
  "tier": "free",
  "rate_limit": 50,
  "rate_period": "day",
  "expires_in_days": 30,
  "message": "Check your email for confirmation"
}
```

**Save your API key securely.** You'll use it for all authenticated requests.

### 3. Make Your First Prediction Request

```bash
curl -H "Authorization: Bearer sk_free_abc123xyz..." \
  https://api.simoracle.com/api/v1/predictions?limit=5
```

Response:
```json
{
  "predictions": [
    {
      "id": "pred_xyz",
      "oracle": "weather",
      "event": "Will it rain in NYC on 2026-04-05?",
      "probability": 0.72,
      "action": "BUY_YES",
      "confidence": 8,
      "timestamp": "2026-04-04T10:30:00Z"
    }
  ],
  "total": 150,
  "limit": 5,
  "offset": 0
}
```

---

## Authentication

All API endpoints except `/api/sample-report` require authentication.

### Bearer Token Authentication

Include your API key in the `Authorization` header:

```bash
Authorization: Bearer sk_free_abc123...
```

**Invalid/Expired Keys:**
- Returns `401 Unauthorized`
- Free tier keys expire after 30 days
- Upgrade to paid tier for extended access

### Rate Limiting

Free tier: **50 requests/day**  
Startup: **1,000 requests/day**  
Professional: **10,000 requests/day**  
Enterprise: **100,000 requests/day + custom**

Rate limit resets daily at **00:00 UTC**.

Response headers include:
```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1712217600
```

When rate limit exceeded:
```json
{
  "detail": "Rate limit exceeded. Free tier: 50 requests/day",
  "status_code": 429,
  "retry_after": 86400
}
```

---

## Public Endpoints

### GET /api/sample-report

No authentication required. Returns sample predictions demonstrating product capabilities.

**Parameters:** None

**Response:** `200 OK`
```json
{
  "report_id": "sample_20260404_xyz",
  "predictions": [...],
  "report_generated_at": "2026-04-04T10:30:00Z",
  "disclaimer": "..."
}
```

---

## API Key Management

### POST /api/v1/keys/generate

Generate a new free tier API key. Auto-expires after 30 days.

**Request:**
```json
{
  "email": "user@company.com",
  "tier": "free"
}
```

**Response:** `200 OK`
```json
{
  "api_key": "sk_free_abc123...",
  "tier": "free",
  "rate_limit": 50,
  "rate_period": "day",
  "expires_in_days": 30,
  "message": "Check your email for confirmation"
}
```

**Notes:**
- Only `tier: "free"` is allowed for self-service generation
- Paid tiers require Stripe checkout
- Welcome email with API key is sent automatically
- 7-day onboarding sequence starts automatically

---

## Predictions API

### GET /api/v1/predictions

List predictions with optional filtering.

**Query Parameters:**
- `oracle` (optional): `weather`, `politics`, `sports`, `crypto`, `macro`
- `status` (optional): `pending`, `resolved`
- `limit` (optional): 1-500, default 50
- `offset` (optional): default 0

**Example:**
```bash
curl -H "Authorization: Bearer sk_free_..." \
  "https://api.simoracle.com/api/v1/predictions?oracle=weather&limit=10"
```

**Response:** `200 OK`
```json
{
  "predictions": [
    {
      "id": "pred_xyz",
      "oracle": "weather",
      "event": "Will it rain in NYC on 2026-04-05?",
      "probability": 0.72,
      "action": "BUY_YES",
      "confidence": 8,
      "timestamp": "2026-04-04T10:30:00Z",
      "outcome": null,
      "outcome_timestamp": null,
      "market_id": "kalshi_xyz",
      "platform": "kalshi"
    }
  ],
  "total": 150,
  "limit": 10,
  "offset": 0
}
```

---

### POST /api/v1/predict

Generate a prediction with multi-model consensus (Claude, Gemini, GPT-4).

**Authentication:** Required

**Request:**
```json
{
  "event": "Will Bitcoin close above $70,000 on 2026-04-06?",
  "oracle": "crypto",
  "deadline": "2026-04-06T23:59:59Z",
  "context": "Optional background context about the market"
}
```

**Response:** `200 OK`
```json
{
  "prediction_id": "pred_20260404xyz",
  "event": "Will Bitcoin close above $70,000 on 2026-04-06?",
  "oracle": "crypto",
  "probability": 0.65,
  "consensus": {
    "models": [
      {
        "model": "claude",
        "probability": 0.68,
        "confidence": 8,
        "reasoning_snippet": "Technical support at $68K..."
      },
      {
        "model": "gemini",
        "probability": 0.62,
        "confidence": 7,
        "reasoning_snippet": "Macro tailwinds from Fed pivot..."
      },
      {
        "model": "gpt4",
        "probability": 0.65,
        "confidence": 8,
        "reasoning_snippet": "Institutional flows positive..."
      }
    ],
    "agreement": "strong",
    "final_probability": 0.65
  },
  "reasoning": "Consensus across 3 models: Technical support at $68K | Macro tailwinds from Fed pivot | Institutional flows positive",
  "timestamp": "2026-04-04T10:30:00Z"
}
```

**Agreement Levels:**
- `strong`: ±0.05 probability spread (models agree closely)
- `moderate`: ±0.12 probability spread
- `weak`: >0.12 spread (models disagree)

---

## Webhooks

Real-time prediction delivery to your endpoints.

### POST /api/v1/webhooks/subscribe

Subscribe to webhook events.

**Request:**
```json
{
  "url": "https://customer.com/webhooks/simoracle",
  "events": ["prediction.created", "prediction.resolved"],
  "secret": "optional_secret_for_hmac_signing"
}
```

**Response:** `201 Created`
```json
{
  "webhook_id": "wh_abc123",
  "url": "https://customer.com/webhooks/simoracle",
  "events": ["prediction.created", "prediction.resolved"],
  "status": "active",
  "secret": "whsec_xyz123..."
}
```

**Webhook Payload:**
```json
{
  "id": "evt_xyz",
  "type": "prediction.created",
  "timestamp": "2026-04-04T10:30:00Z",
  "data": {
    "prediction_id": "pred_xyz",
    "event": "Will Bitcoin close above $70k?",
    "oracle": "crypto",
    "probability": 0.65,
    "action": "BUY_YES",
    "confidence": 8
  }
}
```

**Webhook Headers:**
```
X-SimOracle-Event: prediction.created
X-SimOracle-Signature: sha256=abc123...
X-SimOracle-Delivery: evt_xyz
```

**HMAC Signature Verification (Python):**
```python
import hmac
import hashlib

secret = "whsec_xyz123..."
payload = request.body  # Raw request body as bytes
signature = request.headers.get("X-SimOracle-Signature")

expected = "sha256=" + hmac.new(
    secret.encode(),
    payload,
    hashlib.sha256
).hexdigest()

assert signature == expected  # Signature is valid
```

### GET /api/v1/webhooks

List all active webhook subscriptions.

**Response:** `200 OK`
```json
{
  "webhooks": [
    {
      "webhook_id": "wh_abc123",
      "url": "https://customer.com/webhooks/simoracle",
      "events": ["prediction.created"],
      "status": "active",
      "created_at": "2026-04-04T10:30:00Z",
      "last_test_at": "2026-04-04T10:31:00Z"
    }
  ],
  "total": 1
}
```

### DELETE /api/v1/webhooks/{webhook_id}

Delete a webhook subscription.

**Response:** `200 OK`
```json
{
  "status": "deleted"
}
```

### POST /api/v1/webhooks/{webhook_id}/test

Send a test event to verify webhook is working.

**Response:** `200 OK`
```json
{
  "status": "success",
  "http_status": 200,
  "response": "OK"
}
```

---

## Billing

### POST /api/v1/billing/checkout

Create a Stripe or Lemon Squeezy checkout session for paid tiers.

**Request:**
```json
{
  "tier": "startup",
  "email": "user@company.com",
  "provider": "stripe"
}
```

**Tiers:**
- `startup`: $99/month, 1,000 requests/day
- `professional`: $299/month, 10,000 requests/day
- `enterprise`: $999/month, 100,000 requests/day + webhooks + support

**Response:** `200 OK`
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_xyz...",
  "session_id": "cs_xyz",
  "provider": "stripe",
  "tier": "startup"
}
```

Redirect customer to `checkout_url`. After payment:
1. Stripe webhook upgrades account
2. Confirmation email sent
3. New API key issued (if applicable)

### POST /api/v1/billing/webhooks/stripe

Stripe webhook endpoint. Called automatically by Stripe.

**Events Handled:**
- `customer.subscription.created` — Upgrade account
- `customer.subscription.updated` — Change plan
- `customer.subscription.deleted` — Downgrade to free
- `invoice.payment_succeeded` — Log successful payment
- `invoice.payment_failed` — Alert customer

---

## Usage & Analytics

### GET /api/v1/usage

Get current API usage and rate limit status.

**Response:** `200 OK`
```json
{
  "tier": "free",
  "rate_limit": 50,
  "used": 23,
  "remaining": 27,
  "reset_hours": 24,
  "expires_at": "2026-05-04T10:30:00Z"
}
```

---

## Analytics Endpoints

### GET /api/v1/analytics/whale-activity

Detect large orders (whale activity) across prediction markets.

**Response:** `200 OK`
```json
{
  "score": 72,
  "description": "Analyzed 50 markets, detected 12 signals",
  "details": {
    "markets_analyzed": 50,
    "signals_detected": 12
  },
  "signals": [
    {
      "type": "large_order",
      "market_id": "kalshi_xyz",
      "order_side": "yes",
      "order_size_usd": 50000,
      "confidence": 9,
      "description": "10x median order size for this market",
      "timestamp": "2026-04-04T10:30:00Z"
    }
  ]
}
```

### GET /api/v1/analytics/arbitrage

Find cross-platform arbitrage opportunities.

**Response:** `200 OK`
```json
{
  "opportunities": [
    {
      "market_id": "kalshi_xyz",
      "event": "Will Bitcoin close above $70k?",
      "spread_pct": 5.2,
      "kalshi_price": 0.65,
      "manifesto_price": 0.62,
      "potential_profit_usd": 300,
      "timestamp": "2026-04-04T10:30:00Z"
    }
  ],
  "total": 3,
  "scan_timestamp": "2026-04-04T10:30:00Z"
}
```

---

## Error Handling

All errors return standard JSON format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2026-04-04T10:30:00Z"
}
```

**Common Status Codes:**

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Success |
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Invalid/missing API key |
| 404 | Not Found | Resource doesn't exist |
| 429 | Rate Limited | Wait before retrying |
| 500 | Server Error | Retry with exponential backoff |

---

## SDKs & Libraries

### Python

```python
import httpx
import json

client = httpx.Client(
    base_url="https://api.simoracle.com",
    headers={"Authorization": "Bearer sk_free_..."}
)

# Get predictions
response = client.get("/api/v1/predictions?oracle=weather")
predictions = response.json()

# Generate prediction with consensus
prediction = client.post("/api/v1/predict", json={
    "event": "Will it rain in NYC on 2026-04-05?",
    "oracle": "weather",
}).json()

print(f"Probability: {prediction['probability']}")
print(f"Confidence: {prediction['consensus']['models']}")
```

### JavaScript/TypeScript

```typescript
const API_KEY = "sk_free_...";
const BASE_URL = "https://api.simoracle.com";

async function getPredictions(oracle?: string) {
  const params = new URLSearchParams();
  if (oracle) params.append("oracle", oracle);

  const response = await fetch(
    `${BASE_URL}/api/v1/predictions?${params}`,
    {
      headers: { "Authorization": `Bearer ${API_KEY}` }
    }
  );
  return response.json();
}

async function createPrediction(event: string, oracle: string) {
  const response = await fetch(`${BASE_URL}/api/v1/predict`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      event,
      oracle,
      deadline: new Date(Date.now() + 24*3600000).toISOString()
    })
  });
  return response.json();
}
```

---

## API Roadmap (Post-Launch)

- [ ] Webhook retry with exponential backoff + event history
- [ ] Usage dashboard (customers see detailed breakdown)
- [ ] Batch prediction endpoint (50 events at once)
- [ ] Export predictions to CSV/Parquet
- [ ] OAuth2 for white-label integrations
- [ ] Prediction analytics & accuracy tracking
- [ ] Custom oracle configuration

---

## Support

- **Docs:** https://simoracle.com/docs
- **Email:** api-support@simoracle.com
- **Status Page:** https://status.simoracle.com
- **Discord:** https://discord.gg/simoracle

---

## Changelog

### v0.1.0 (MVP Launch - Week 1)
- Sample report generator (no auth)
- Free API tier with key generation
- Rate limiting (50 req/day)
- Multi-model consensus (Claude, Gemini, GPT-4)
- Webhook subscriptions + delivery
- Stripe checkout integration
- Email onboarding sequence
- Analytics endpoints (whale activity, arbitrage, insider signals)

---

**Last Updated:** April 4, 2026
