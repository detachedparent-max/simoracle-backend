"""
Database query helpers for SimOracle
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from database.schema import get_db_connection


class PredictionQueries:
    @staticmethod
    def create_prediction(
        oracle: str,
        event: str,
        probability: float,
        action: str,
        confidence: int,
        market_id: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> str:
        """Create a new prediction record"""
        prediction_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO predictions
            (id, oracle, event, probability, action, confidence, market_id, platform)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (prediction_id, oracle, event, probability, action, confidence, market_id, platform))

        conn.commit()
        conn.close()
        return prediction_id

    @staticmethod
    def get_predictions(
        oracle: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Fetch predictions with optional filtering"""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM predictions WHERE 1=1"
        params = []

        if oracle:
            query += " AND oracle = ?"
            params.append(oracle)

        if status == "pending":
            query += " AND outcome IS NULL"
        elif status == "resolved":
            query += " AND outcome IS NOT NULL"

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        predictions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return predictions

    @staticmethod
    def get_prediction_by_id(prediction_id: str) -> Optional[Dict[str, Any]]:
        """Get a single prediction by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None

    @staticmethod
    def update_prediction_outcome(prediction_id: str, outcome: str):
        """Mark a prediction as resolved"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE predictions
            SET outcome = ?, outcome_timestamp = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (outcome, prediction_id))
        conn.commit()
        conn.close()


class ReasoningQueries:
    @staticmethod
    def create_reasoning_log(
        prediction_id: str,
        model: str,
        catalyst_primary: str,
        catalyst_secondary: Optional[str] = None,
        confidence_driver: Optional[str] = None,
        data_sources: Optional[List[str]] = None,
        consensus_status: str = "pending",
        reasoning_text: Optional[str] = None,
    ) -> str:
        """Create a reasoning log entry"""
        reasoning_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()

        data_sources_json = json.dumps(data_sources or [])

        cursor.execute("""
            INSERT INTO reasoning_logs
            (id, prediction_id, model, catalyst_primary, catalyst_secondary,
             confidence_driver, data_sources, consensus_status, reasoning_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reasoning_id, prediction_id, model, catalyst_primary, catalyst_secondary,
            confidence_driver, data_sources_json, consensus_status, reasoning_text
        ))

        conn.commit()
        conn.close()
        return reasoning_id

    @staticmethod
    def get_reasoning_for_prediction(prediction_id: str) -> List[Dict[str, Any]]:
        """Get all reasoning logs for a prediction"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM reasoning_logs
            WHERE prediction_id = ?
            ORDER BY timestamp DESC
        """, (prediction_id,))

        logs = []
        for row in cursor.fetchall():
            log = dict(row)
            log['data_sources'] = json.loads(log['data_sources']) if log['data_sources'] else []
            logs.append(log)

        conn.close()
        return logs


class PositionQueries:
    @staticmethod
    def upsert_position(
        user_id: str,
        market_id: str,
        market_name: str,
        shares: int,
        entry_price: float,
        current_price: float,
    ):
        """Create or update a position"""
        position_id = f"{user_id}_{market_id}"
        pnl = shares * (current_price - entry_price)
        pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO user_positions
            (id, user_id, market_id, market_name, shares, entry_price, current_price, pnl, pnl_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (position_id, user_id, market_id, market_name, shares, entry_price, current_price, pnl, pnl_pct))

        conn.commit()
        conn.close()

    @staticmethod
    def get_user_positions(user_id: str) -> List[Dict[str, Any]]:
        """Get all positions for a user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM user_positions
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (user_id,))

        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return positions


class AnalyticsQueries:
    @staticmethod
    def create_snapshot(
        whale_activity_score: int,
        whale_activity_details: Dict[str, Any],
        arb_opportunities: List[Dict[str, Any]],
        insider_signals: List[Dict[str, Any]],
    ) -> str:
        """Create an analytics snapshot"""
        snapshot_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO analytics_snapshots
            (id, whale_activity_score, whale_activity_details,
             arb_opportunity_count, arb_opportunities,
             insider_signal_count, insider_signals)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id,
            whale_activity_score,
            json.dumps(whale_activity_details),
            len(arb_opportunities),
            json.dumps(arb_opportunities),
            len(insider_signals),
            json.dumps(insider_signals),
        ))

        conn.commit()
        conn.close()
        return snapshot_id

    @staticmethod
    def get_latest_snapshot() -> Optional[Dict[str, Any]]:
        """Get the most recent analytics snapshot"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM analytics_snapshots
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        snapshot = dict(result)
        snapshot['whale_activity_details'] = json.loads(snapshot['whale_activity_details']) if snapshot['whale_activity_details'] else {}
        snapshot['arb_opportunities'] = json.loads(snapshot['arb_opportunities']) if snapshot['arb_opportunities'] else []
        snapshot['insider_signals'] = json.loads(snapshot['insider_signals']) if snapshot['insider_signals'] else []

        return snapshot


class MarketQueries:
    @staticmethod
    def create_market_snapshot(
        market_id: str,
        market_name: str,
        platform: str,
        yes_price: float,
        no_price: float,
        yes_liquidity: float,
        no_liquidity: float,
        yes_orderbook: Optional[Dict] = None,
        no_orderbook: Optional[Dict] = None,
    ) -> str:
        """Create a market data snapshot"""
        snapshot_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO market_snapshots
            (id, market_id, market_name, platform, yes_price, no_price,
             yes_liquidity, no_liquidity, yes_orderbook, no_orderbook)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, market_id, market_name, platform,
            yes_price, no_price, yes_liquidity, no_liquidity,
            json.dumps(yes_orderbook or {}),
            json.dumps(no_orderbook or {}),
        ))

        conn.commit()
        conn.close()
        return snapshot_id

    @staticmethod
    def get_market_history(market_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get market price history"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT * FROM market_snapshots
            WHERE market_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (market_id, cutoff_time))

        snapshots = []
        for row in cursor.fetchall():
            snapshot = dict(row)
            snapshot['yes_orderbook'] = json.loads(snapshot['yes_orderbook']) if snapshot['yes_orderbook'] else {}
            snapshot['no_orderbook'] = json.loads(snapshot['no_orderbook']) if snapshot['no_orderbook'] else {}
            snapshots.append(snapshot)

        conn.close()
        return snapshots
