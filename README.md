# SimOracle Backend - Institutional Prediction Engine

FastAPI-based analytics engine powering SimOracle's real-time prediction trading and institutional intelligence platform.

## Overview

SimOracle Backend provides:
- **Real-time prediction tracking** from Kalshi and secondary platforms
- **Advanced analytics**: Whale activity detection, arbitrage scanning, insider pattern recognition
- **Causal reasoning export** for compliance and audit trails
- **Multi-oracle support**: Weather, Politics, Sports, Equities
- **Institutional API** for backtesting, strategy analysis, and reporting

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/thikay/simoracle-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
# KALSHI_USERNAME, KALSHI_PASSWORD, etc.
```

### 3. Run Server

```bash
python3 app.py
# Or with uvicorn directly:
# uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Server starts at: **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
simoracle-backend/
├── app.py                      # FastAPI application entry point
├── config.py                   # Configuration & environment
├── requirements.txt            # Python dependencies
│
├── database/
│   ├── schema.py              # SQLite schema initialization
│   └── queries.py             # Database query helpers
│
├── analytics/
│   ├── whale_detector.py      # Detect large order patterns
│   ├── arbitrage_scanner.py   # Cross-platform price gaps
│   ├── insider_patterns.py    # Confidence jump detection
│   └── reasoning_exporter.py  # JSON/CSV export + audit trails
│
├── market_feeds/
│   ├── kalshi.py              # Kalshi API client (async)
│   ├── manifesto.py           # Manifesto API (placeholder)
│   └── polymarket.py          # Polymarket API (placeholder)
│
└── api/
    ├── routes.py              # FastAPI endpoint handlers
    └── models.py              # Pydantic request/response schemas
```

## Database

SQLite database at `~/.simoracle/data.db` with tables:
- **predictions** — Core prediction records (oracle, event, probability, action, confidence)
- **reasoning_logs** — Causal chains (primary catalyst, confidence driver, model, data sources)
- **user_positions** — Current holdings (market_id, shares, entry_price, current_price, PnL)
- **market_snapshots** — Historical market data (prices, liquidity, orderbooks)
- **analytics_snapshots** — Whale activity + arbitrage opportunities
- **whale_activity_history** — Detailed whale event records
- **backtest_results** — Backtesting performance metrics

All tables auto-initialize on first run.

## API Endpoints

### Predictions
- `GET /api/v1/predictions` — List predictions (filter by oracle/status)
- `GET /api/v1/predictions/{id}/reasoning` — Full causal chain for one prediction

### Analytics
- `GET /api/v1/analytics/whale-activity` — Whale order detection (0-100 score)
- `GET /api/v1/analytics/arbitrage` — Cross-platform price gaps (>5% spreads)
- `GET /api/v1/analytics/insider-signals` — Confidence jump patterns

### Market Data
- `GET /api/v1/markets/{market_id}/orderbook` — Live orderbook depth
- `GET /api/v1/user/positions` — User's current positions + PnL

### Export
- `GET /api/v1/export/reasoning?oracle=weather&format=json` — JSON export
- `GET /api/v1/export/reasoning?oracle=weather&format=csv` — CSV export
- `GET /api/v1/export/audit-trail/{prediction_id}` — Compliance audit trail

### Health
- `GET /api/v1/health` — Service status + database + Kalshi connection

## Key Features

### 1. Whale Activity Detector
Analyzes orderbooks for:
- Large orders (>$10K USD)
- Unusual order sizes (10x median)
- Bid-ask imbalance (>70/30 threshold)
- Returns activity score 0-100 + detailed signals

### 2. Arbitrage Scanner
Cross-platform price comparison:
- Kalshi vs Manifesto vs Polymarket
- Flags spreads >5%
- Checks liquidity (min $1K on each side)
- Estimates profit per tradeable contract

### 3. Insider Pattern Recognition
Detects suspicious confidence patterns:
- Confidence jumps (>30% change in 1 hour)
- Model agreement analysis (multi-LLM consensus)
- Early accuracy correlation (high confidence → correct prediction)
- Strength scored 0-100

### 4. Reasoning Exporter
Compliance-ready causal chains:
- Full audit trail (primary catalyst → secondary → confidence driver)
- Multi-model consensus tracking
- Data provenance (sources cited)
- JSON and CSV formats
- Suitable for regulatory filing

## Configuration

Edit `config.py` to customize:
- Database path: `DATABASE_PATH`
- Whale thresholds: `WHALE_ACTIVITY_MIN_USD`, `WHALE_IMBALANCE_THRESHOLD`
- Arbitrage minimum spread: `ARBITRAGE_MIN_SPREAD_PCT`
- Insider signal sensitivity: `INSIDER_CONFIDENCE_JUMP_PCT`
- Market feed polling intervals

## Authentication & Security

### Kalshi Integration
- Username/password auth (generates bearer token)
- Async HTTP client with timeout protection
- Graceful fallback to read-only mode if unavailable

### API Endpoints
- No auth required for MVP (add API keys before production)
- CORS enabled for all origins (restrict in production)
- Error responses include minimal detail in non-debug mode

## Performance Considerations

### Database
- SQLite suitable for MVP (<1M predictions)
- Indexed queries on: oracle, timestamp, market_id, prediction_id
- Automatic connection pooling in queries
- WAL mode for concurrent access

### Analytics
- Whale detector: O(n) on orderbook size
- Arbitrage scanner: O(m) on market count
- Insider patterns: O(p) on recent predictions
- Cache latest snapshot in-memory if needed (future optimization)

### API
- Async all market feed operations
- Streaming responses for large exports (future)
- Connection pooling for Kalshi API

## Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific endpoint
pytest tests/test_api.py::test_list_predictions -v

# Coverage report
pytest tests/ --cov=. --cov-report=html
```

## Deployment

### Local Development
```bash
python3 app.py
```

### Production (Vercel)
Add to `vercel.json`:
```json
{
  "buildCommand": "pip install -r requirements.txt",
  "functions": {
    "api/**/*.py": {
      "runtime": "python3.11"
    }
  }
}
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "app.py"]
```

## Roadmap

**MVP (Launch Week):**
- ✅ Kalshi integration (market data + positions)
- ✅ Whale activity detector
- ✅ Arbitrage scanner
- ✅ Reasoning exporter
- ✅ API endpoint suite

**Post-Launch (Week 2+):**
- WebSocket real-time streams (instead of polling)
- Manifesto & Polymarket feed integration
- Backtesting engine (accuracy + calibration scoring)
- Premium data upload feature
- Confidence gating thresholds per oracle

## Architecture Notes

### Multi-Model Reasoning
Predictions include reasoning from Claude, Gemini, GPT-4. The API agent handles:
- Routing requests to each model
- Collecting confidence scores
- Storing results in `reasoning_logs`

Backend stores and exports these for compliance.

### Causal Attribution
Core competitive moat: Every prediction includes:
1. **Primary Catalyst** — #1 reason for prediction
2. **Secondary Catalyst** — #2 reason
3. **Confidence Driver** — What makes you confident?
4. **Data Sources** — URLs/references cited
5. **Model Consensus** — Did all models agree?

### Real-Time Feeds
Kalshi: WebSocket (future) or polling every 5 seconds (current)
Manifesto: HTTP polling every 30 seconds
Polymarket: HTTP polling every 60 seconds

## Troubleshooting

### Database Error: "disk I/O error"
- Ensure `~/.simoracle/` directory exists and is writable
- Check disk space: `df -h`

### Kalshi Auth Failed
- Verify credentials in `.env`
- Check network connectivity: `curl https://api.kalshi.com/v1/health`
- Service continues in read-only mode

### "market not found" Error
- Kalshi market_id may have expired or closed
- Check `/api/v1/health` for Kalshi connection status

## Contributing

Backend maintains:
- Type hints on all functions (use `mypy` for checking)
- Docstrings on all public classes/functions
- Async/await patterns for all I/O
- Database transactions for consistency

## License

SimOracle — 2025
