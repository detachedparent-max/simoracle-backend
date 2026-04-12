# SimOracle Backend Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Services                            │
├─────────────────────────────────────────────────────────────────────┤
│  OpenRouter        Stripe              SendGrid/Mailgun             │
│  (Claude,          (Payments)          (Email)                      │
│   Gemini,          Webhook             Newsletter                   │
│   GPT-4)           Handler                                          │
└────────────┬────────────────────────┬────────────────────────────────┘
             │                        │
             ▼                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Port 8000)                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              API Routes (Router)                             │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │                                                              │   │
│  │  ▸ api/routes.py          [Original Predictions API]        │   │
│  │    └─ /api/v1/predictions                                   │   │
│  │    └─ /api/v1/analytics/*                                   │   │
│  │    └─ /api/v1/user/positions                                │   │
│  │    └─ /api/v1/health                                        │   │
│  │                                                              │   │
│  │  ▸ api/integration_routes.py [NEW - All Integrations]       │   │
│  │    └─ /api/sample-report        [Sample predictions]        │   │
│  │    └─ /api/v1/keys/generate     [Free API key]              │   │
│  │    └─ /api/v1/predict           [Multi-model consensus]     │   │
│  │    └─ /api/v1/billing/*         [Stripe checkout]           │   │
│  │    └─ /api/v1/webhooks/*        [Webhook management]        │   │
│  │    └─ /api/v1/usage             [Rate limit status]         │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Core Integration Modules                        │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │                                                              │   │
│  │  ▸ api/sample_report.py                                      │   │
│  │    └─ generate_sample_report() → 6 realistic predictions    │   │
│  │                                                              │   │
│  │  ▸ api/auth.py                                              │   │
│  │    ├─ APIKeyManager                                          │   │
│  │    │  ├─ generate_api_key()                                  │   │
│  │    │  ├─ validate_api_key()                                  │   │
│  │    │  └─ check_rate_limit()                                  │   │
│  │    └─ validate_bearer_token() [FastAPI Dependency]           │   │
│  │                                                              │   │
│  │  ▸ api/llm_orchestration.py                                  │   │
│  │    └─ LLMOrchestrator                                        │   │
│  │       ├─ predict() → calls 3 models in parallel             │   │
│  │       ├─ _aggregate_consensus() → mean + agreement scoring  │   │
│  │       └─ retry logic for timeouts                            │   │
│  │                                                              │   │
│  │  ▸ api/billing.py                                            │   │
│  │    └─ BillingManager                                         │   │
│  │       ├─ create_checkout_session() [Stripe/Lemon Squeezy]   │   │
│  │       ├─ process_stripe_webhook() [Auto-upgrade on payment] │   │
│  │       └─ upgrade_tier()                                      │   │
│  │                                                              │   │
│  │  ▸ api/email_onboarding.py                                   │   │
│  │    └─ EmailOnboarding                                        │   │
│  │       ├─ send_welcome_email() [SendGrid/Mailgun]             │   │
│  │       ├─ schedule_onboarding_sequence() [7-day email]        │   │
│  │       └─ _render_welcome_template()                          │   │
│  │                                                              │   │
│  │  ▸ api/webhooks.py                                           │   │
│  │    └─ WebhookManager                                         │   │
│  │       ├─ subscribe() [Create webhook subscription]           │   │
│  │       ├─ dispatch_event() [Real-time delivery]               │   │
│  │       ├─ _deliver_webhook() [With retry + HMAC signing]      │   │
│  │       └─ test_webhook() [Verify endpoint working]            │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Authentication Middleware                       │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  ▸ Bearer Token Validation                                   │   │
│  │  ▸ Rate Limit Enforcement (50 req/day for free)             │   │
│  │  ▸ Request Logging                                           │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
             ▲                        ▲
             │                        │
┌────────────┴─────────────────────────┴───────────────────────────────┐
│                    Database Layer (SQLite)                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Location: ~/.simoracle/data.db                                     │
│                                                                      │
│  Core Tables:                   Integration Tables:                 │
│  ├─ predictions                 ├─ api_keys                         │
│  ├─ reasoning_logs              ├─ api_usage                        │
│  ├─ user_positions              ├─ subscriptions                    │
│  ├─ market_snapshots            ├─ billing_events                   │
│  ├─ whale_activity_history      ├─ webhook_subscriptions            │
│  └─ backtest_results            ├─ webhook_deliveries               │
│                                 ├─ onboarding_schedule              │
│                                 └─ onboarding_events                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Sample Report Flow (No Auth)

```
User Visit
    │
    ▼
GET /api/sample-report
    │
    ▼
generate_sample_report()
    │
    ├─ Create 6 realistic predictions (hard-coded)
    ├─ Include reasoning + catalysts
    ├─ Set confidence scores (7-9)
    │
    ▼
Return JSON Response
    │
    ▼
Browser Displays Report
(No signup friction!)
    │
    ▼
User impressed → Signs up for API key
```

### 2. Free API Key Flow

```
User submits email
    │
    ▼
POST /api/v1/keys/generate
    │
    ├─ Generate key (sk_free_<random>)
    ├─ Hash key (SHA256)
    ├─ Store in api_keys table with:
    │  ├─ email
    │  ├─ tier: "free"
    │  ├─ rate_limit: 50 requests/day
    │  ├─ expires_at: 30 days from now
    │
    ├─ Send welcome email via SendGrid
    │  ├─ API key in email (safe to copy)
    │  ├─ 3-step quick start
    │  ├─ Documentation links
    │
    ├─ Schedule 7-day email sequence
    │  ├─ Day 0: Welcome + key
    │  ├─ Day 1: First prediction report
    │  ├─ Day 3: API quota warning
    │  ├─ Day 7: Institutional trial pitch
    │
    ▼
Return API key response
    │
    ▼
User receives email + starts building
```

### 3. Multi-Model Prediction Flow

```
User: POST /api/v1/predict
  {
    "event": "Will Bitcoin close above $70k?",
    "oracle": "crypto"
  }
    │
    ▼
validate_bearer_token()
  ├─ Hash API key
  ├─ Lookup in api_keys table
  ├─ Check rate limit (50 req/day)
  └─ If all OK: proceed, else return 401/429
    │
    ▼
LLMOrchestrator.predict()
  ├─ Build prompt (structured, JSON-only)
  ├─ Call 3 models in parallel via OpenRouter:
  │  ├─ Claude Sonnet 4
  │  ├─ Gemini 2.0 Flash
  │  └─ GPT-4 Turbo
  │
  ├─ Parse responses (extract probability + confidence)
  ├─ Handle timeouts gracefully (require 2/3 minimum)
  │
  ├─ Aggregate consensus:
  │  ├─ Calculate mean probability
  │  ├─ Calculate standard deviation
  │  ├─ Determine agreement level (strong/moderate/weak)
  │  └─ Combine reasoning from all 3 models
  │
    ▼
Return response with full consensus breakdown
  {
    "prediction_id": "pred_xyz",
    "probability": 0.65,
    "consensus": {
      "models": [
        {"model": "claude", "probability": 0.68, "confidence": 8},
        {"model": "gemini", "probability": 0.62, "confidence": 7},
        {"model": "gpt4", "probability": 0.65, "confidence": 8}
      ],
      "agreement": "strong",
      "final_probability": 0.65
    }
  }
    │
    ▼
If webhooks subscribed:
  └─ Dispatch prediction.created event to all subscribers
```

### 4. Webhook Delivery Flow

```
New prediction generated
    │
    ▼
WebhookManager.dispatch_event()
    │
    ├─ Query webhook_subscriptions table
    ├─ Filter by:
    │  ├─ status = 'active'
    │  ├─ events contains 'prediction.created'
    │  └─ email matches (if applicable)
    │
    ├─ For each webhook:
    │  │
    │  ├─ Create payload:
    │  │  {
    │  │    "id": "evt_xyz",
    │  │    "type": "prediction.created",
    │  │    "timestamp": "2026-04-04T...",
    │  │    "data": { prediction details }
    │  │  }
    │  │
    │  ├─ Generate HMAC-SHA256 signature
    │  │  secret = stored in webhook_subscriptions
    │  │  signature = hmac.new(secret, payload).hexdigest()
    │  │
    │  ├─ POST to customer webhook URL
    │  │  Headers:
    │  │  ├─ X-SimOracle-Event: prediction.created
    │  │  ├─ X-SimOracle-Signature: sha256=<sig>
    │  │  └─ X-SimOracle-Delivery: evt_xyz
    │  │
    │  ├─ Log delivery attempt
    │  │  ├─ If status 200-204: mark as delivered
    │  │  ├─ If 5xx: schedule retry (5s, 30s, 5m)
    │  │  └─ If 4xx: log error, no retry
    │  │
    │  ├─ Customer webhook endpoint:
    │  │  ├─ Receives POST with payload
    │  │  ├─ Verifies HMAC signature
    │  │  ├─ Processes prediction
    │  │  └─ Returns 200 OK
    │
    ▼
Delivery logged to webhook_deliveries table
```

### 5. Billing & Subscription Flow

```
User clicks "Upgrade to Startup"
    │
    ▼
POST /api/v1/billing/checkout
    │
    ├─ Validate tier (startup/professional/enterprise)
    ├─ Create Stripe checkout session
    │  ├─ variant_id: stripe price ID
    │  ├─ customer_email: user@company.com
    │  ├─ success_url: simoracle.com/success
    │  └─ cancel_url: simoracle.com/pricing
    │
    ▼
Return checkout_url: "https://checkout.stripe.com/pay/cs_xyz"
    │
    ▼
Browser redirects to Stripe checkout
    │
    ▼
User enters payment details
    │
    ▼
Payment successful
    │
    ▼
Stripe webhook: POST /api/v1/billing/webhooks/stripe
  {
    "type": "customer.subscription.created",
    "data": {
      "object": {
        "customer": "cus_xyz",
        "subscription": "sub_xyz",
        "status": "active"
      }
    }
  }
    │
    ├─ Webhook received + signature verified
    ├─ Extract customer email + subscription ID
    ├─ Insert into subscriptions table:
    │  ├─ tier: "startup"
    │  ├─ stripe_customer_id: cus_xyz
    │  ├─ stripe_subscription_id: sub_xyz
    │  └─ status: "active"
    │
    ├─ Upgrade api_keys entry:
    │  ├─ Update rate_limit_requests: 1000
    │  └─ Clear expires_at (paid tiers don't expire)
    │
    ├─ Send confirmation email
    │  ├─ Welcome to Startup tier
    │  ├─ New API key (if applicable)
    │  └─ Webhook access info
    │
    ▼
User now has 1,000 requests/day instead of 50
```

---

## Rate Limiting Architecture

```
Every API request (authenticated):

1. Extract API key from Authorization header
   │
   ▼
2. Hash key: api_key_hash = SHA256(api_key)
   │
   ▼
3. Query api_keys table:
   │  SELECT rate_limit_requests, rate_limit_period_hours
   │  WHERE api_key_hash = ?
   │
   ▼
4. Count requests in current period:
   │  cutoff_time = now() - rate_limit_period_hours
   │  SELECT COUNT(*) FROM api_usage
   │  WHERE api_key_hash = ? AND timestamp > cutoff_time
   │
   ▼
5. Check: is request_count < rate_limit_requests?
   │  ├─ YES: Allow request, log to api_usage
   │  └─ NO: Return 429 Too Many Requests
   │
   ▼
6. Store response headers:
   │  X-RateLimit-Limit: 50
   │  X-RateLimit-Used: 23
   │  X-RateLimit-Remaining: 27
   │  X-RateLimit-Reset: 1712217600 (Unix timestamp)
```

---

## Security Model

### API Key Security

```
Generation:
  ├─ Client: Never shown to user in logs
  ├─ Plaintext: Shown once in API response (only at creation)
  ├─ Storage: SHA256 hash stored in database
  └─ Transport: HTTPS only

Usage:
  ├─ Header: Authorization: Bearer sk_free_...
  ├─ Validation: Hash incoming key, compare to database hashes
  ├─ Rotation: Expire free keys after 30 days
  └─ Revocation: Can manually delete from api_keys table

Best Practices (documented in email + docs):
  ├─ Never commit to version control
  ├─ Never share via email or chat
  ├─ Rotate regularly
  └─ Delete when no longer needed
```

### Webhook Security

```
Signature Verification:

1. Stripe sends webhook POST + X-Webhook-Signature header
2. We calculate expected signature:
   │  expected = hmac.new(
   │      webhook_secret,
   │      raw_request_body,
   │      hashlib.sha256
   │  ).hexdigest()
3. Compare: expected == received_signature
4. If match: Trust webhook, process request
   └─ If mismatch: Reject (potential spoofing)

Customer webhook signature (similar):

1. We send prediction event to customer URL
2. Include X-SimOracle-Signature header:
   │  signature = hmac.new(
   │      customer_secret,
   │      json_payload,
   │      hashlib.sha256
   │  ).hexdigest()
3. Customer verifies signature same way
4. Only process if signature valid
```

---

## Scalability Considerations

### Current Bottlenecks

1. **LLM Latency:** Parallel calls to 3 models = ~3-5s per prediction
   - Fix: Cache predictions by (event, oracle, date)

2. **SQLite Concurrency:** Single-file database, limited write throughput
   - Fix: Migrate to PostgreSQL (same schema) for production

3. **Email Service:** SendGrid API calls are synchronous
   - Fix: Queue email jobs (Celery/RQ), process asynchronously

4. **Webhook Delivery:** Retry logic is blocking
   - Fix: Move to separate worker queue (job scheduler)

### Recommended Production Upgrades

```
Week 2:
  ├─ Migrate SQLite → PostgreSQL
  ├─ Add Redis cache (predictions + API keys)
  ├─ Async email queue (Celery/RQ)
  └─ Webhook retry scheduler (separate process)

Week 3+:
  ├─ Add CDN (predictions, sample reports)
  ├─ Rate limiting via Redis (not SQLite)
  ├─ Batch prediction endpoint
  └─ Analytics aggregation (time-series DB)
```

---

## Testing Strategy

### Unit Tests

```python
# test_sample_report.py
def test_sample_report_returns_6_predictions()
def test_sample_report_probability_between_0_1()
def test_sample_report_includes_disclaimer()

# test_auth.py
def test_api_key_generation()
def test_api_key_validation()
def test_rate_limiting_50_per_day()
def test_rate_limit_reset_at_midnight_utc()

# test_llm_orchestration.py
def test_predict_calls_3_models_in_parallel()
def test_consensus_aggregation()
def test_agreement_scoring()
def test_graceful_failure_if_1_model_fails()

# test_webhooks.py
def test_webhook_subscription()
def test_webhook_delivery()
def test_hmac_signature_verification()
def test_webhook_retry_logic()
```

### Integration Tests

```python
# test_integration.py
def test_full_signup_flow():
    # 1. Generate sample report
    # 2. Create API key
    # 3. Make prediction request
    # 4. Verify rate limiting
    # 5. Upgrade to paid tier

def test_webhook_end_to_end():
    # 1. Subscribe to webhooks
    # 2. Generate prediction
    # 3. Verify webhook delivered
    # 4. Verify signature valid
```

---

## Monitoring & Observability

### Metrics to Track

| Metric | Alert Threshold |
|--------|-----------------|
| API Uptime | <99.9% |
| Response Time (p95) | >2s |
| Error Rate | >5% |
| Rate Limit Violations | >10% of traffic |
| Webhook Delivery Success | <95% |
| LLM Model Agreement | Track trend |
| Free→Paid Conversion | Target >15% |
| Email Open Rate | Target >30% |

### Logging

```python
# All requests logged with:
├─ timestamp
├─ endpoint
├─ method
├─ status_code
├─ response_time_ms
├─ api_key_tier (if applicable)
├─ error_message (if failed)
└─ user_agent

# Webhook deliveries logged with:
├─ webhook_id
├─ event_type
├─ http_status
├─ response_body (first 500 chars)
├─ attempt_number
├─ next_retry_time
└─ success_or_failure
```

---

**Architecture Version:** 1.0  
**Last Updated:** April 4, 2026  
**Designed For:** Launch Week MVP
