// Vercel Functions handler for SimOracle stub backend
// Uses Web Request/Response API (not Express)

export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const { pathname, searchParams } = new URL(req.url, 'http://localhost');

  // Health check
  if (pathname === '/health' && req.method === 'GET') {
    return res.status(200).json({ status: 'ok' });
  }

  // Sample report
  if (pathname === '/api/v1/sample-report' && req.method === 'GET') {
    return res.status(200).json({
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
  }

  // Stripe checkout
  if (pathname === '/api/v1/billing/checkout' && req.method === 'POST') {
    const body = await req.json();
    const tier = body?.tier || 'startup';
    const tiers = {
      startup: { price: 99, name: 'Intelligence Dashboard' },
      pro: { price: 299, name: 'Professional Suite' },
      enterprise: { price: 999, name: 'Enterprise Custom' }
    };
    const tierInfo = tiers[tier] || tiers.startup;

    return res.status(200).json({
      session_url: `https://checkout.stripe.com/pay/cs_test_${Math.random().toString(36).slice(2, 14)}`,
      tier,
      price: tierInfo.price,
      name: tierInfo.name
    });
  }

  // API key generation
  if (pathname === '/api/v1/keys/generate' && req.method === 'POST') {
    const body = await req.json();
    const email = body?.email || 'user@example.com';

    return res.status(200).json({
      api_key: `sk_live_${Math.random().toString(36).slice(2, 32)}`,
      email,
      rate_limit: 50,
      rate_limit_period: 'day',
      tier: 'free',
      created_at: new Date().toISOString(),
      message: 'API key generated. 50 requests per day limit.'
    });
  }

  // Whale activity
  if (pathname === '/api/v1/analytics/whale-activity' && req.method === 'GET') {
    return res.status(200).json({
      timestamp: new Date().toISOString(),
      whale_score: 8.2,
      large_orders: [
        { size: 50000, side: 'YES', confidence: 9, market: 'NYC Weather' },
        { size: 30000, side: 'NO', confidence: 7, market: 'Policy Vote' },
        { size: 25000, side: 'YES', confidence: 8, market: 'Sports Event' }
      ],
      trend: 'bullish'
    });
  }

  // Arbitrage
  if (pathname === '/api/v1/analytics/arbitrage' && req.method === 'GET') {
    return res.status(200).json({
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
  }

  // Insider patterns
  if (pathname === '/api/v1/analytics/insider-patterns' && req.method === 'GET') {
    return res.status(200).json({
      timestamp: new Date().toISOString(),
      signals: [
        { pattern: 'Unusual timing cluster', confidence: 9, market: 'NYC Weather', direction: 'bullish' }
      ]
    });
  }

  // Predictions
  if (pathname === '/api/v1/predictions' && req.method === 'GET') {
    return res.status(200).json({
      predictions: [
        { id: 'pred_001', oracle: 'weather', event: 'NYC > 75F', probability: 0.72, confidence: 8, status: 'active' }
      ],
      total: 1
    });
  }

  // Stripe webhook
  if (pathname === '/api/v1/billing/webhooks/stripe' && req.method === 'POST') {
    return res.status(200).json({ status: 'received' });
  }

  // Rate limit
  if (pathname.match(/^\/api\/v1\/user\/.*\/rate-limit$/) && req.method === 'GET') {
    return res.status(200).json({
      requests_used: 25,
      requests_limit: 50,
      remaining: 25
    });
  }

  // Root
  if (pathname === '/' && req.method === 'GET') {
    return res.status(200).json({
      name: 'SimOracle Stub Backend',
      version: '0.1.0',
      status: 'running'
    });
  }

  // 404
  return res.status(404).json({ error: 'Not found' });
}
