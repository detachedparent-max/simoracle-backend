"""
FastAPI route handlers for SimOracle backend
"""
import json
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, File, UploadFile
from api.models import (
    PredictionResponse, PredictionListResponse, PredictionReasoningResponse,
    UserPositionsResponse, PositionResponse,
    WhaleActivityResponse, ArbitrageListResponse, ArbitrageOpportunityResponse,
    InsiderSignalsResponse, HealthResponse, ErrorResponse,
    OrderbookResponse, OrderLevel,
)
from database.queries import (
    PredictionQueries, ReasoningQueries, PositionQueries, AnalyticsQueries, MarketQueries
)
from analytics.whale_detector import WhaleDetector
from analytics.arbitrage_scanner import ArbitrageScanner
from analytics.insider_patterns import InsiderPatterns
from analytics.reasoning_exporter import ReasoningExporter
from market_feeds.kalshi import get_kalshi_client
from database.schema import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["SimOracle"])


# ============================================================================
# PREDICTIONS ENDPOINTS
# ============================================================================

@router.get("/predictions", response_model=PredictionListResponse)
async def list_predictions(
    oracle: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List predictions with optional filtering
    - oracle: 'weather', 'politics', 'sports', 'equity'
    - status: 'pending', 'resolved'
    """
    try:
        predictions = PredictionQueries.get_predictions(
            oracle=oracle, status=status, limit=limit, offset=offset
        )

        response_preds = [
            PredictionResponse(
                id=p['id'],
                oracle=p['oracle'],
                event=p['event'],
                probability=p['probability'],
                action=p['action'],
                confidence=p['confidence'],
                timestamp=p['timestamp'],
                outcome=p.get('outcome'),
                outcome_timestamp=p.get('outcome_timestamp'),
                market_id=p.get('market_id'),
                platform=p.get('platform'),
            )
            for p in predictions
        ]

        return PredictionListResponse(
            predictions=response_preds,
            total=len(predictions),
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"List predictions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/{prediction_id}/reasoning", response_model=PredictionReasoningResponse)
async def get_prediction_reasoning(prediction_id: str):
    """Get complete reasoning chain for a prediction"""
    try:
        prediction = PredictionQueries.get_prediction_by_id(prediction_id)
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")

        export = ReasoningExporter.export_prediction_reasoning_json(prediction_id)
        return PredictionReasoningResponse(**export)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get reasoning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MARKET DATA ENDPOINTS
# ============================================================================

@router.get("/markets/{market_id}/orderbook", response_model=OrderbookResponse)
async def get_market_orderbook(market_id: str):
    """Get orderbook for a market"""
    try:
        kalshi = await get_kalshi_client()
        orderbook = await kalshi.get_orderbook(market_id)

        if not orderbook:
            raise HTTPException(status_code=404, detail="Market not found")

        bids = [OrderLevel(price=b['price'], qty=b['qty']) for b in orderbook.get('bids', [])]
        asks = [OrderLevel(price=a['price'], qty=a['qty']) for a in orderbook.get('asks', [])]

        # Calculate mid-price
        if bids and asks:
            mid_price = (bids[0].price + asks[0].price) / 2
        else:
            mid_price = 0.5

        return OrderbookResponse(
            market_id=market_id,
            bids=bids,
            asks=asks,
            mid_price=mid_price,
            timestamp=datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get orderbook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/whale-activity", response_model=WhaleActivityResponse)
async def get_whale_activity():
    """Get current whale activity score and details"""
    try:
        # Get latest market snapshots (mock data for MVP)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM market_snapshots
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        snapshots = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not snapshots:
            return WhaleActivityResponse(
                score=0,
                description="No market data available",
                details={},
                signals=[],
            )

        # Analyze whale activity across markets
        all_signals = []
        scores = []

        for snapshot in snapshots:
            yes_ob = json.loads(snapshot['yes_orderbook']) if snapshot['yes_orderbook'] else {}
            no_ob = json.loads(snapshot['no_orderbook']) if snapshot['no_orderbook'] else {}

            score, signals = WhaleDetector.analyze_orderbook(
                snapshot['market_id'],
                yes_ob, no_ob,
                snapshot['yes_price'], snapshot['no_price']
            )

            scores.append(score)
            all_signals.extend(signals)

        overall_score = int(sum(scores) / len(scores)) if scores else 0

        return WhaleActivityResponse(
            score=overall_score,
            description=f"Analyzed {len(snapshots)} markets, detected {len(all_signals)} signals",
            details={'markets_analyzed': len(snapshots), 'signals_detected': len(all_signals)},
            signals=[
                {
                    'type': s.signal_type,
                    'market_id': s.market_id,
                    'order_side': s.order_side,
                    'order_size_usd': s.order_size_usd,
                    'confidence': s.confidence,
                    'description': s.description,
                    'timestamp': s.timestamp.isoformat(),
                }
                for s in all_signals[:20]  # Return top 20 signals
            ]
        )
    except Exception as e:
        logger.error(f"Get whale activity failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/arbitrage", response_model=ArbitrageListResponse)
async def get_arbitrage_opportunities():
    """Get cross-platform arbitrage opportunities"""
    try:
        # Get latest market snapshots
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT market_id FROM market_snapshots
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        market_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        all_opportunities = []

        for market_id in market_ids[:20]:  # Scan top 20 markets
            market_history = MarketQueries.get_market_history(market_id, hours=1)
            if not market_history:
                continue

            latest = market_history[0]

            # For MVP, use Kalshi as primary, others are mock
            opportunities = ArbitrageScanner.scan_platforms(
                market_id,
                kalshi_price=latest.get('yes_price', 0.5),
                kalshi_liquidity=latest.get('yes_liquidity', 1000),
                manifesto_price=None,  # Would fetch from Manifesto API
                manifesto_liquidity=None,
                polymarket_price=None,
                polymarket_liquidity=None,
            )

            all_opportunities.extend(opportunities)

        formatted = ArbitrageScanner.aggregate_opportunities(all_opportunities)

        return ArbitrageListResponse(
            opportunities=[
                ArbitrageOpportunityResponse(**opp) for opp in formatted
            ],
            total=len(formatted),
            scan_timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Get arbitrage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/insider-signals", response_model=InsiderSignalsResponse)
async def get_insider_signals():
    """Get insider pattern signals from recent predictions"""
    try:
        signals = InsiderPatterns.scan_all_recent_predictions()
        formatted = InsiderPatterns.format_signals(signals)

        return InsiderSignalsResponse(
            signals=[s for s in formatted if s['strength'] > 40],  # Filter weak signals
            total=len(signals),
            scan_timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Get insider signals failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# POSITIONS ENDPOINTS
# ============================================================================

@router.get("/user/positions", response_model=UserPositionsResponse)
async def get_user_positions(user_id: str = Query(...)):
    """Get user's current trading positions"""
    try:
        positions = PositionQueries.get_user_positions(user_id)

        response_positions = [
            PositionResponse(
                id=p['id'],
                market_id=p['market_id'],
                market_name=p['market_name'],
                shares=p['shares'],
                entry_price=p['entry_price'],
                current_price=p['current_price'],
                pnl=p['pnl'],
                pnl_pct=p['pnl_pct'],
                timestamp=p['timestamp'],
            )
            for p in positions
        ]

        total_pnl = sum(p.pnl for p in positions)
        total_entry_value = sum(p.entry_price * p.shares for p in positions)
        total_pnl_pct = (total_pnl / total_entry_value * 100) if total_entry_value > 0 else 0

        return UserPositionsResponse(
            positions=response_positions,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
        )
    except Exception as e:
        logger.error(f"Get positions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@router.get("/export/reasoning")
async def export_reasoning(
    oracle: Optional[str] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Export predictions with reasoning chains
    format: 'json' or 'csv'
    """
    try:
        if format == "json":
            return ReasoningExporter.export_predictions_json(oracle, limit)
        else:
            csv_content = ReasoningExporter.export_to_csv(oracle, limit)
            return {
                "format": "csv",
                "content": csv_content,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/audit-trail/{prediction_id}")
async def export_audit_trail(prediction_id: str, include_raw: bool = Query(False)):
    """
    Export compliance-ready audit trail for a prediction
    """
    try:
        audit_trail = ReasoningExporter.generate_audit_trail(
            prediction_id, include_raw_reasoning=include_raw
        )

        if not audit_trail:
            raise HTTPException(status_code=404, detail="Prediction not found")

        return audit_trail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export audit trail failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        db_ready = True
    except:
        db_ready = False

    # Check Kalshi connection
    try:
        kalshi = await get_kalshi_client()
        kalshi_connected = kalshi.auth_token is not None
    except:
        kalshi_connected = False

    return HealthResponse(
        status="healthy" if db_ready else "degraded",
        timestamp=datetime.now().isoformat(),
        version="0.1.0",
        database_ready=db_ready,
        kalshi_connected=kalshi_connected,
    )
