# SimOracle Backend - Deployment & Integration Guide

## Launch Week Status

**Phase:** MVP Complete - Ready for launch
**Date:** April 4, 2025
**Status:** All core components operational

## What's Included (MVP)

### ✅ Completed
1. **Database Layer** — SQLite with 7 core tables
   - Predictions, reasoning logs, positions, market snapshots, analytics, whale history, backtest results
   - Auto-initialization on first run
   - Indexed queries for performance

2. **Analytics Engine** — Four core modules
   - **Whale Detector** — Identifies large order patterns (>$10K, 10x median, >70/30 imbalance)
   - **Arbitrage Scanner** — Cross-platform price gaps (>5% spreads)
   - **Insider Patterns** — Confidence jumps (>30% in 1hr), model agreement, early accuracy
   - **Reasoning Exporter** — JSON/CSV causal chains for compliance

3. **Market Feeds** — Kalshi API client (async)
   - Authenticate with username/password
   - Fetch markets, orderbooks, positions, order history
   - Place/cancel orders
   - Graceful fallback to read-only if auth fails

4. **FastAPI Application** — Production-ready server
   - 13 core endpoints covering predictions, analytics, positions, export
   - Pydantic request/response validation
   - CORS enabled for frontend integration
   - Health check endpoint
   - Comprehensive error handling

5. **API Endpoints** (13 total)
   - `GET /api/v1/predictions` — List predictions (filter by oracle/status)
   - `GET /api/v1/predictions/{id}/reasoning` — Full causal chain
   - `GET /api/v1/markets/{market_id}/orderbook` — Live orderbook
   - `GET /api/v1/analytics/whale-activity` — Whale detection (0-100 score)
   - `GET /api/v1/analytics/arbitrage` — Arbitrage opportunities
   - `GET /api/v1/analytics/insider-signals` — Insider patterns
   - `GET /api/v1/user/positions` — User holdings + PnL
   - `GET /api/v1/export/reasoning?format=json|csv` — Export predictions
   - `GET /api/v1/export/audit-trail/{prediction_id}` — Compliance audit
   - `GET /api/v1/health` — Service status
   - Plus 3 more for future enhancements

### 🔮 Future Enhancements (Post-Launch)
- WebSocket real-time streams (instead of polling)
- Manifesto & Polymarket feed integration
- Backtesting engine (accuracy + calibration scoring)
- Premium user data upload feature

## Deployment Options

### Option 1: Local Development (Recommended for MVP)

```bash
cd /Users/thikay/simoracle-backend

# Quick start
./start.sh

# Manual start
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with credentials
python3 app.py
```

Server runs on: **http://127.0.0.1:8000**
- API Docs: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Option 2: Vercel (Production)

**Steps:**
1. Create `/Users/thikay/simoracle-backend/vercel.json`:
```json
{
  "buildCommand": "/opt/homebrew/bin/python3.11 -m pip install -r requirements.txt",
  "outputDirectory": ".",
  "env": {
    "KALSHI_USERNAME": "@KALSHI_USERNAME",
    "KALSHI_PASSWORD": "@KALSHI_PASSWORD",
    "KALSHI_API_KEY": "@KALSHI_API_KEY"
  }
}
```

2. Deploy:
```bash
cd /Users/thikay/simoracle-backend
vercel --prod
```

3. Set environment variables in Vercel dashboard with actual credentials

### Option 3: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python3", "app.py"]
```

Build and run:
```bash
docker build -t simoracle-backend .
docker run -p 8000:8000 \
  -e KALSHI_USERNAME=your_username \
  -e KALSHI_PASSWORD=your_password \
  simoracle-backend
```

## Frontend Integration

### NextJS Integration (simoracle/app/)

```typescript
// lib/api.ts
export async function fetchPredictions(oracle?: string) {
  const params = new URLSearchParams();
  if (oracle) params.append('oracle', oracle);
  
  const response = await fetch(`http://localhost:8000/api/v1/predictions?${params}`);
  return response.json();
}

export async function fetchWhaleActivity() {
  const response = await fetch('http://localhost:8000/api/v1/analytics/whale-activity');
  return response.json();
}

export async function fetchArbitrageOpportunities() {
  const response = await fetch('http://localhost:8000/api/v1/analytics/arbitrage');
  return response.json();
}

export async function fetchReasoningChain(predictionId: string) {
  const response = await fetch(`http://localhost:8000/api/v1/predictions/${predictionId}/reasoning`);
  return response.json();
}
```

### React Component Example

```typescript
// components/PredictionsList.tsx
import { useEffect, useState } from 'react';
import { fetchPredictions } from '@/lib/api';

export function PredictionsList({ oracle }: { oracle?: string }) {
  const [predictions, setPredictions] = useState([]);
  
  useEffect(() => {
    fetchPredictions(oracle).then(data => {
      setPredictions(data.predictions);
    });
  }, [oracle]);
  
  return (
    <div className="space-y-4">
      {predictions.map(pred => (
        <div key={pred.id} className="border rounded p-4">
          <h3 className="font-bold">{pred.event}</h3>
          <p>Probability: {(pred.probability * 100).toFixed(1)}%</p>
          <p>Action: {pred.action}</p>
          <p>Confidence: {pred.confidence}/10</p>
        </div>
      ))}
    </div>
  );
}
```

## Configuration

### Environment Variables (.env)

```env
# Server
HOST=127.0.0.1
PORT=8000
DEBUG=False

# Kalshi (Required for trading)
KALSHI_USERNAME=your_username
KALSHI_PASSWORD=your_password
KALSHI_API_KEY=optional_api_key

# Manifesto (Optional)
MANIFESTO_API_KEY=your_key

# OpenRouter (For multi-LLM routing, handled by API agent)
OPENROUTER_API_KEY=your_key
```

### Database Customization (config.py)

```python
# Whale Detection Thresholds
WHALE_ACTIVITY_MIN_USD = 10000  # Detect orders >$10K
WHALE_IMBALANCE_THRESHOLD = 70  # 70/30 bid-ask ratio
WHALE_SIZE_MULTIPLIER = 10      # 10x median order size

# Arbitrage Thresholds
ARBITRAGE_MIN_SPREAD_PCT = 5.0  # Flag >5% spreads
ARBITRAGE_MIN_LIQUIDITY_USD = 1000  # Min liquidity per side

# Insider Pattern Thresholds
INSIDER_CONFIDENCE_JUMP_PCT = 30  # Flag >30% jumps in 1 hour

# Market Feed Polling (seconds)
KALSHI_FEED_INTERVAL_SECONDS = 1
MANIFESTO_POLL_INTERVAL_SECONDS = 30
POLYMARKET_POLL_INTERVAL_SECONDS = 60
```

## Data Flow

```
Frontend (Next.js)
    ↓
Backend API (FastAPI)
    ├─ Database (SQLite)
    │  ├─ predictions
    │  ├─ reasoning_logs
    │  └─ market_snapshots
    │
    ├─ Analytics Engine
    │  ├─ whale_detector
    │  ├─ arbitrage_scanner
    │  ├─ insider_patterns
    │  └─ reasoning_exporter
    │
    └─ Market Feeds
       ├─ Kalshi API
       ├─ Manifesto API
       └─ Polymarket API
```

## API Agent Integration

The API agent (multi-LLM orchestrator) should:

1. **Accept prediction requests** from Frontend
2. **Route to multiple models** (Claude, Gemini, GPT-4 via OpenRouter)
3. **Collect confidence scores** from each model
4. **Call backend to store** reasoning:
   ```bash
   POST /api/v1/predictions
   {
     "oracle": "weather",
     "event": "Will it rain in NYC on 2026-04-05?",
     "probability": 0.72,
     "action": "BUY_YES",
     "confidence": 8,
     "market_id": "abc123",
     "platform": "kalshi"
   }
   ```

5. **Store reasoning logs** (one per model):
   ```bash
   POST /api/v1/reasoning
   {
     "prediction_id": "pred_123",
     "model": "claude-opus",
     "catalyst_primary": "NWS forecast shows 65% chance rain",
     "catalyst_secondary": "Historical accuracy for this region is 72%",
     "confidence_driver": "Multiple weather models agree",
     "data_sources": ["NWS forecast", "historical data", "satellite imagery"],
     "consensus_status": "strong"
   }
   ```

## Monitoring & Debugging

### Health Check
```bash
curl http://localhost:8000/api/v1/health

# Response:
{
  "status": "healthy",
  "database_ready": true,
  "kalshi_connected": true,
  "timestamp": "2025-04-04T15:30:00Z"
}
```

### View Database
```bash
sqlite3 ~/.simoracle/data.db
> SELECT COUNT(*) FROM predictions;
> SELECT * FROM analytics_snapshots ORDER BY timestamp DESC LIMIT 1;
```

### Check Logs
```bash
tail -f /Users/thikay/simoracle-backend/app.log
```

### Test Specific Endpoint
```bash
# Get predictions
curl "http://localhost:8000/api/v1/predictions?oracle=weather&limit=5"

# Get whale activity
curl "http://localhost:8000/api/v1/analytics/whale-activity"

# Export CSV
curl "http://localhost:8000/api/v1/export/reasoning?format=csv&oracle=weather" > predictions.csv
```

## Performance Notes

### Current Bottlenecks (Post-Launch Optimizations)
1. **Polling instead of WebSocket** — Adds 5-10s latency. Future: WebSocket streams
2. **SQLite single-file** — Works well for MVP, scale to PostgreSQL if >1M predictions
3. **In-memory orderbook analysis** — Cache latest 50 markets for faster scanning

### Scalability Roadmap
- Week 2-3: Add Redis caching for market data
- Week 4: Switch to PostgreSQL for multi-region deployment
- Week 6: WebSocket streams + Redis pub/sub

## Troubleshooting

### "Database locked" Error
```bash
# Reset database
rm ~/.simoracle/data.db
# Restart server (auto-reinitialize)
python3 app.py
```

### Kalshi Auth Failed
- Verify credentials in `.env`
- Check network: `curl https://api.kalshi.com/v1/health`
- Server continues in read-only mode

### Slow Predictions Endpoint
- Check database size: `sqlite3 ~/.simoracle/data.db "SELECT COUNT(*) FROM predictions;"`
- If >100K predictions, add pagination or archiving

### CORS Errors (Frontend)
- Ensure backend is running: `curl http://localhost:8000/`
- Check allowed origins in `app.py` (currently `*` for dev)

## Launch Checklist

- [ ] Copy `.env.example` → `.env`
- [ ] Add Kalshi credentials to `.env`
- [ ] Run `./start.sh` and verify no errors
- [ ] Test `http://localhost:8000/docs`
- [ ] Test predict endpoint: `curl http://localhost:8000/api/v1/predictions`
- [ ] Test whale activity: `curl http://localhost:8000/api/v1/analytics/whale-activity`
- [ ] Wire up Frontend to Backend URLs
- [ ] Deploy to Vercel (or Docker/local)
- [ ] Update Frontend `.env` with backend URL
- [ ] Smoke test full prediction flow
- [ ] Monitor logs for errors: `tail -f app.log`

## Support

**Backend Code Location:** `/Users/thikay/simoracle-backend/`
**Database:** `~/.simoracle/data.db`
**Logs:** Terminal output when running `python3 app.py`

**Next Steps:**
1. API Agent builds multi-LLM orchestrator
2. Frontend integrates prediction endpoints
3. LiveTrading bot connects to `/api/v1/predictions` + `/api/v1/user/positions`
4. Institutional customers access `/api/v1/export/audit-trail` for compliance

---

**Built for SimOracle Launch — April 4, 2025**
