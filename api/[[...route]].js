export default function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const path = req.url;

  // Health
  if (path === '/health') {
    return res.json({ status: 'ok' });
  }

  // Sample Report
  if (path === '/v1/sample-report') {
    return res.json([
      { id: 1, oracle: 'Weather', event: 'Temperature spike', probability: 85, confidence: 9, action: 'BUY_YES', reasoning: 'NOAA forecast shows significant deviation' },
      { id: 2, oracle: 'Politics', event: 'Election momentum shift', probability: 72, confidence: 7, action: 'BUY_YES', reasoning: 'Polling data indicates trend change' },
      { id: 3, oracle: 'Sports', event: 'Team injury impact', probability: 78, confidence: 8, action: 'BUY_NO', reasoning: 'Historical data shows injury recovery rates' },
      { id: 4, oracle: 'Markets', event: 'Earnings surprise', probability: 65, confidence: 6, action: 'BUY_YES', reasoning: 'SEC filings show unusual activity' },
      { id: 5, oracle: 'Arbitrage', event: 'Dutch book opportunity', probability: 91, confidence: 10, action: 'BUY_YES', reasoning: 'YES+NO combined odds exceed 100%' },
      { id: 6, oracle: 'Whale Activity', event: 'Large position accumulation', probability: 88, confidence: 9, action: 'BUY_YES', reasoning: 'Order book analysis detected accumulation' },
    ]);
  }

  if (req.method === 'POST' && path === '/v1/billing/checkout') {
    const { tier } = req.body;
    return res.json({
      session_url: `https://checkout.stripe.com/pay/cs_test_${Math.random().toString(36).slice(2, 15)}`,
      tier,
      price: tier === 'all' ? 499 : 89,
      name: tier === 'all' ? 'All Oracles' : 'Single Oracle',
    });
  }

  if (req.method === 'POST' && path === '/v1/keys/generate') {
    const { email } = req.body;
    return res.json({
      api_key: `sk_live_${Math.random().toString(36).slice(2, 15)}`,
      email,
      rate_limit: 50,
      tier: 'free',
      created_at: new Date().toISOString(),
      message: 'API key generated successfully',
    });
  }

  res.status(404).json({ error: 'Not found' });
}
