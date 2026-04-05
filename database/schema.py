"""
SQLite schema initialization for SimOracle
"""
import sqlite3
from pathlib import Path
from config import DATABASE_PATH


def init_database():
    """Initialize SQLite database with all required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Core predictions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id TEXT PRIMARY KEY,
        oracle TEXT NOT NULL,
        event TEXT NOT NULL,
        probability REAL NOT NULL,
        action TEXT NOT NULL,
        confidence INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        outcome TEXT,
        outcome_timestamp DATETIME,
        market_id TEXT,
        platform TEXT
    )
    """)

    # Reasoning and causal attribution
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reasoning_logs (
        id TEXT PRIMARY KEY,
        prediction_id TEXT NOT NULL,
        model TEXT NOT NULL,
        catalyst_primary TEXT,
        catalyst_secondary TEXT,
        confidence_driver TEXT,
        data_sources TEXT,
        consensus_status TEXT,
        reasoning_text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (prediction_id) REFERENCES predictions(id)
    )
    """)

    # User positions (read-only from Kalshi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_positions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        market_id TEXT NOT NULL,
        market_name TEXT,
        shares INTEGER,
        entry_price REAL,
        current_price REAL,
        pnl REAL,
        pnl_pct REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Market data snapshots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_snapshots (
        id TEXT PRIMARY KEY,
        market_id TEXT NOT NULL,
        market_name TEXT,
        platform TEXT,
        yes_price REAL,
        no_price REAL,
        yes_liquidity REAL,
        no_liquidity REAL,
        yes_orderbook TEXT,
        no_orderbook TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Analytics snapshots (whale activity, arbitrage)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analytics_snapshots (
        id TEXT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        whale_activity_score INTEGER,
        whale_activity_details TEXT,
        arb_opportunity_count INTEGER,
        arb_opportunities TEXT,
        insider_signal_count INTEGER,
        insider_signals TEXT
    )
    """)

    # Backtesting results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backtest_results (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        strategy TEXT,
        date_range TEXT,
        accuracy REAL,
        calibration REAL,
        total_trades INTEGER,
        winning_trades INTEGER,
        profit_projection REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Whale activity history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS whale_activity_history (
        id TEXT PRIMARY KEY,
        market_id TEXT NOT NULL,
        order_size REAL,
        order_side TEXT,
        order_price REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        confidence_score INTEGER
    )
    """)

    # Create indices for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_oracle ON predictions(oracle)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reasoning_prediction ON reasoning_logs(prediction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics_snapshots(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_market ON whale_activity_history(market_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_snapshots_timestamp ON market_snapshots(timestamp)")

    conn.commit()
    conn.close()


def get_db_connection():
    """Get a SQLite connection with row factory"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
