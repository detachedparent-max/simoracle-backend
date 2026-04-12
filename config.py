"""
Configuration for SimOracle backend
"""
import os
from pathlib import Path

# Database
DATABASE_DIR = Path.home() / ".simoracle"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = str(DATABASE_DIR / "data.db")

# API Keys
KALSHI_API_KEY = os.getenv("KALSHI_API_KEY", "")
KALSHI_RSA_KEY_PATH = os.getenv("KALSHI_RSA_KEY_PATH", "")
KALSHI_USERNAME = os.getenv("KALSHI_USERNAME", "")
KALSHI_PASSWORD = os.getenv("KALSHI_PASSWORD", "")

MANIFESTO_API_KEY = os.getenv("MANIFESTO_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Analytics thresholds
WHALE_ACTIVITY_MIN_USD = 10000  # Detect orders >$10K
WHALE_IMBALANCE_THRESHOLD = 70  # 70/30 bid-ask imbalance
WHALE_SIZE_MULTIPLIER = 10  # 10x median order size

ARBITRAGE_MIN_SPREAD_PCT = 5.0  # Flag spreads >5%
ARBITRAGE_MIN_LIQUIDITY_USD = 1000  # Ignore if <$1K liquidity

INSIDER_CONFIDENCE_JUMP_PCT = 30  # Flag >30% confidence change in 1hr
INSIDER_SIGNAL_LOOKBACK_HOURS = 24

# Market feed polling
KALSHI_FEED_INTERVAL_SECONDS = 1  # Real-time (WebSocket)
MANIFESTO_POLL_INTERVAL_SECONDS = 30
POLYMARKET_POLL_INTERVAL_SECONDS = 60

# Reasoning
MULTI_LLM_MODELS = ["claude-opus", "gemini-pro", "gpt-4-turbo"]
MIN_CONSENSUS_MODELS = 2  # Require agreement from 2+ models
