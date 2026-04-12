// Express stub server for SimOracle backend
// Run: node server.js
// Listens on http://localhost:3001

const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Sample report
app.get('/api/v1/sample-report', (req, res) => {
  res.json({
    predictions: [
      {
        id: 'pred_001',
        oracle: 'weather',
        event: 'NYC Temperature > 75F on Apr 10',
        probability: 0.72,
        confidence: 8,
        action: 'BUY_YES',
        reasoning: 'NWS forecast shows high-pressure system. Historical accuracy 85%.'
      },
      {
        id: 'pred_002',
        oracle: 'arbitrage',
        event: 'Kalshi-Polymarket price gap > 5%',
        probability: 0.68,
        confidence: 7,
        action: 'EXPLOIT_ARB',
        reasoning: 'Cross-platform analysis detects YES overpriced on Kalshi.'
      },
      {
        id: 'pred_003',
        oracle: 'whale',
        event: 'Institutional order imbalance',
        probability: 0.81,
        confidence: 9,
        action: 'FOLLOW_WHALE',
        reasoning: '$250K order cluster on YES side. Insider signal 9/10.'
      },
      {
        id: 'pred_004',
        oracle: 'politics',
        event: 'Policy announcement probability',
        probability: 0.55,
        confidence: 6,
        action: 'WAIT',
        reasoning: 'Multi-LLM consensus shows conflicting signals.'
      },
      {
        id: 'pred_005',
        oracle: 'sports',
        event: 'Team A victory probability',
        probability: 0.64,
        confidence: 7,
        action: 'BUY_YES',
        reasoning: 'Undervaluing home field. Edge 16.3%.'
      },
      {
        id: 'pred_006',
        oracle: 'equity',
        event: 'Stock > $150 by EOY',
        probability: 0.73,
        confidence: 7,
        action: 'BUY_YES',
        reasoning: 'Technical + insider patterns suggest 73%.'
      }
    ]
  });
});

// Stripe checkout
app.post('/api/v1/billing/checkout', (req, res) => {
  const { tier = 'startup' } = req.body;
  const tiers = {
    startup: { price: 99, name: 'Intelligence Dashboard' },
    pro: { price: 299, name: 'Professional Suite' },
    enterprise: { price: 999, name: 'Enterprise Custom' }
  };
  const tierInfo = tiers[tier] || tiers.startup;

  res.json({
    session_url: `https://checkout.stripe.com/pay/cs_test_${Math.random().toString(36).slice(2, 14)}`,
    tier,
    price: tierInfo.price,
    name: tierInfo.name
  });
});

// API key generation
app.post('/api/v1/keys/generate', (req, res) => {
  const { email = 'user@example.com' } = req.body;

  res.json({
    api_key: `sk_live_${Math.random().toString(36).slice(2, 32)}`,
    email,
    rate_limit: 50,
    rate_limit_period: 'day',
    tier: 'free',
    created_at: new Date().toISOString(),
    message: 'API key generated. 50 requests per day limit.'
  });
});

// Whale activity
app.get('/api/v1/analytics/whale-activity', (req, res) => {
  res.json({
    timestamp: new Date().toISOString(),
    whale_score: 8.2,
    large_orders: [
      { size: 50000, side: 'YES', confidence: 9, market: 'NYC Weather' },
      { size: 30000, side: 'NO', confidence: 7, market: 'Policy Vote' },
      { size: 25000, side: 'YES', confidence: 8, market: 'Sports Event' }
    ],
    trend: 'bullish'
  });
});

// Arbitrage
app.get('/api/v1/analytics/arbitrage', (req, res) => {
  res.json({
    timestamp: new Date().toISOString(),
    opportunities: [
      {
        event: 'NYC Temperature > 75F',
        kalshi_yes: 0.68,
        polymarket_yes: 0.65,
        spread: 0.03,
        edge: 'EXPLOIT_BUY_POLYMARKET',
        risk_free: true
      }
    ]
  });
});

// Insider patterns
app.get('/api/v1/analytics/insider-patterns', (req, res) => {
  res.json({
    timestamp: new Date().toISOString(),
    signals: [
      { pattern: 'Unusual timing cluster', confidence: 9, market: 'NYC Weather', direction: 'bullish' }
    ]
  });
});

// Predictions
app.get('/api/v1/predictions', (req, res) => {
  res.json({
    predictions: [
      { id: 'pred_001', oracle: 'weather', event: 'NYC > 75F', probability: 0.72, confidence: 8, status: 'active' }
    ],
    total: 1
  });
});

// Stripe webhook
app.post('/api/v1/billing/webhooks/stripe', (req, res) => {
  res.json({ status: 'received' });
});

// Rate limit
app.get('/api/v1/user/:api_key/rate-limit', (req, res) => {
  res.json({
    requests_used: 25,
    requests_limit: 50,
    remaining: 25
  });
});

// Root
app.get('/', (req, res) => {
  res.json({
    name: 'SimOracle Stub Backend',
    version: '0.1.0',
    status: 'running'
  });
});

// 404
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Start server
app.listen(PORT, () => {
  console.log(`✓ SimOracle backend listening on http://localhost:${PORT}`);
  console.log(`✓ CORS enabled for all origins`);
  console.log(`\nEndpoints:`);
  console.log(`  GET  /health`);
  console.log(`  GET  /api/v1/sample-report`);
  console.log(`  POST /api/v1/billing/checkout`);
  console.log(`  POST /api/v1/keys/generate`);
  console.log(`  GET  /api/v1/analytics/whale-activity`);
  console.log(`  GET  /api/v1/analytics/arbitrage`);
  console.log(`  GET  /api/v1/analytics/insider-patterns`);
  console.log(`  GET  /api/v1/predictions`);
  console.log(`  POST /api/v1/billing/webhooks/stripe`);
  console.log(`  GET  /api/v1/user/:api_key/rate-limit`);
});
