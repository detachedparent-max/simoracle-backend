// Vercel serverless function using Web Request/Response API
export async function GET(req) {
  const url = new URL(req.url);
  const pathname = url.pathname;

  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };

  // Health check
  if (pathname === '/health' || pathname === '/api/health') {
    return new Response(JSON.stringify({ status: 'ok' }), { headers });
  }

  // Sample Report
  if (pathname === '/v1/sample-report' || pathname === '/api/v1/sample-report') {
    return new Response(JSON.stringify([
      { id: 1, oracle: 'Weather', event: 'Temperature spike', probability: 85, confidence: 9, action: 'BUY_YES', reasoning: 'NOAA forecast shows significant deviation' },
      { id: 2, oracle: 'Politics', event: 'Election momentum shift', probability: 72, confidence: 7, action: 'BUY_YES', reasoning: 'Polling data indicates trend change' },
      { id: 3, oracle: 'Sports', event: 'Team injury impact', probability: 78, confidence: 8, action: 'BUY_NO', reasoning: 'Historical data shows injury recovery rates' },
      { id: 4, oracle: 'Markets', event: 'Earnings surprise', probability: 65, confidence: 6, action: 'BUY_YES', reasoning: 'SEC filings show unusual activity' },
      { id: 5, oracle: 'Arbitrage', event: 'Dutch book opportunity', probability: 91, confidence: 10, action: 'BUY_YES', reasoning: 'YES+NO combined odds exceed 100%' },
      { id: 6, oracle: 'Whale Activity', event: 'Large position accumulation', probability: 88, confidence: 9, action: 'BUY_YES', reasoning: 'Order book analysis detected accumulation' },
    ]), { headers });
  }

  // Analytics endpoints
  if (pathname === '/v1/analytics/whale-activity' || pathname === '/api/v1/analytics/whale-activity') {
    return new Response(JSON.stringify({ data: 'whale activity data' }), { headers });
  }

  if (pathname === '/v1/analytics/arbitrage' || pathname === '/api/v1/analytics/arbitrage') {
    return new Response(JSON.stringify({ data: 'arbitrage opportunities' }), { headers });
  }

  if (pathname === '/v1/analytics/insider-patterns' || pathname === '/api/v1/analytics/insider-patterns') {
    return new Response(JSON.stringify({ data: 'insider patterns' }), { headers });
  }

  // Predictions list
  if (pathname === '/v1/predictions' || pathname === '/api/v1/predictions') {
    return new Response(JSON.stringify({ predictions: [] }), { headers });
  }

  // Rate limit check
  const rateLimit = pathname.match(/^\/(?:api\/)?v1\/user\/(.+)\/rate-limit$/);
  if (rateLimit) {
    return new Response(JSON.stringify({ requests_today: 0, limit: 50 }), { headers });
  }

  // 404
  return new Response(JSON.stringify({ error: 'Not found' }), { status: 404, headers });
}

export async function POST(req) {
  const url = new URL(req.url);
  const pathname = url.pathname;

  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };

  try {
    const body = await req.json();

    // Checkout
    if (pathname === '/v1/billing/checkout' || pathname === '/api/v1/billing/checkout') {
      const { tier } = body;
      return new Response(JSON.stringify({
        session_url: `https://checkout.stripe.com/pay/cs_test_${Math.random().toString(36).slice(2, 15)}`,
        tier,
        price: tier === 'all' ? 499 : 89,
        name: tier === 'all' ? 'All Oracles' : 'Single Oracle',
      }), { headers });
    }

    // Generate API Key
    if (pathname === '/v1/keys/generate' || pathname === '/api/v1/keys/generate') {
      const { email } = body;
      return new Response(JSON.stringify({
        api_key: `sk_live_${Math.random().toString(36).slice(2, 15)}`,
        email,
        rate_limit: 50,
        tier: 'free',
        created_at: new Date().toISOString(),
        message: 'API key generated successfully',
      }), { headers });
    }

    // Stripe webhook
    if (pathname === '/v1/billing/webhooks/stripe' || pathname === '/api/v1/billing/webhooks/stripe') {
      return new Response(JSON.stringify({ status: 'received' }), { headers });
    }
  } catch (err) {
    return new Response(JSON.stringify({ error: 'Invalid request body' }), { status: 400, headers });
  }

  // 404
  return new Response(JSON.stringify({ error: 'Not found' }), { status: 404, headers });
}

export async function OPTIONS(req) {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
