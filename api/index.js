// Vercel serverless function wrapper for Express app
import express from 'express';
import cors from 'cors';

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Sample Report
app.get('/api/v1/sample-report', (req, res) => {
  res.json([
    { id: 1, oracle: 'Weather', event: 'Temperature spike', probability: 85, confidence: 9, action: 'BUY_YES', reasoning: 'NOAA forecast shows significant deviation' },
    { id: 2, oracle: 'Politics', event: 'Election momentum shift', probability: 72, confidence: 7, action: 'BUY_YES', reasoning: 'Polling data indicates trend change' },
    { id: 3, oracle: 'Sports', event: 'Team injury impact', probability: 78, confidence: 8, action: 'BUY_NO', reasoning: 'Historical data shows injury recovery rates' },
    { id: 4, oracle: 'Markets', event: 'Earnings surprise', probability: 65, confidence: 6, action: 'BUY_YES', reasoning: 'SEC filings show unusual activity' },
    { id: 5, oracle: 'Arbitrage', event: 'Dutch book opportunity', probability: 91, confidence: 10, action: 'BUY_YES', reasoning: 'YES+NO combined odds exceed 100%' },
    { id: 6, oracle: 'Whale Activity', event: 'Large position accumulation', probability: 88, confidence: 9, action: 'BUY_YES', reasoning: 'Order book analysis detected accumulation' },
  ]);
});

// Checkout
app.post('/api/v1/billing/checkout', (req, res) => {
  const { tier } = req.body;
  res.json({
    session_url: `https://checkout.stripe.com/pay/cs_test_${Math.random().toString(36).slice(2, 15)}`,
    tier,
    price: tier === 'all' ? 499 : 89,
    name: tier === 'all' ? 'All Oracles' : 'Single Oracle',
  });
});

// Generate API Key
app.post('/api/v1/keys/generate', (req, res) => {
  const { email } = req.body;
  res.json({
    api_key: `sk_live_${Math.random().toString(36).slice(2, 15)}`,
    email,
    rate_limit: 50,
    tier: 'free',
    created_at: new Date().toISOString(),
    message: 'API key generated successfully',
  });
});

// Analytics endpoints
app.get('/api/v1/analytics/whale-activity', (req, res) => {
  res.json({ data: 'whale activity data' });
});

app.get('/api/v1/analytics/arbitrage', (req, res) => {
  res.json({ data: 'arbitrage opportunities' });
});

app.get('/api/v1/analytics/insider-patterns', (req, res) => {
  res.json({ data: 'insider patterns' });
});

// Predictions list
app.get('/api/v1/predictions', (req, res) => {
  res.json({ predictions: [] });
});

// Stripe webhook
app.post('/api/v1/billing/webhooks/stripe', (req, res) => {
  res.json({ status: 'received' });
});

// Rate limit check
app.get('/api/v1/user/:api_key/rate-limit', (req, res) => {
  res.json({ requests_today: 0, limit: 50 });
});

export default app;
