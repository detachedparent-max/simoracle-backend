"""
Whale activity detector - identifies unusual order patterns
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from config import (
    WHALE_ACTIVITY_MIN_USD,
    WHALE_IMBALANCE_THRESHOLD,
    WHALE_SIZE_MULTIPLIER,
)
from database.queries import MarketQueries
import json


@dataclass
class WhaleSignal:
    market_id: str
    signal_type: str  # 'large_order', 'imbalance', 'unusual_size'
    order_side: str  # 'BID' or 'ASK'
    order_size_usd: float
    order_price: float
    confidence: int  # 0-100
    description: str
    timestamp: datetime


class WhaleDetector:
    """Detects whale (large trader) activity patterns"""

    @staticmethod
    def analyze_orderbook(
        market_id: str,
        yes_orderbook: Dict[str, Any],
        no_orderbook: Dict[str, Any],
        yes_price: float,
        no_price: float,
    ) -> tuple[int, List[WhaleSignal]]:
        """
        Analyze orderbook for whale activity
        Returns: (activity_score 0-100, list of signals)
        """
        signals = []
        scores = []

        # Analyze YES orderbook
        yes_signals, yes_score = WhaleDetector._analyze_side(
            market_id, yes_orderbook, yes_price, "YES"
        )
        signals.extend(yes_signals)
        scores.append(yes_score)

        # Analyze NO orderbook
        no_signals, no_score = WhaleDetector._analyze_side(
            market_id, no_orderbook, no_price, "NO"
        )
        signals.extend(no_signals)
        scores.append(no_score)

        # Check for bid-ask imbalance
        imbalance_signals, imbalance_score = WhaleDetector._check_imbalance(
            yes_orderbook, no_orderbook, yes_price, no_price
        )
        signals.extend(imbalance_signals)
        scores.append(imbalance_score)

        # Aggregate score (0-100)
        overall_score = int(sum(scores) / len(scores)) if scores else 0

        return overall_score, signals

    @staticmethod
    def _analyze_side(
        market_id: str,
        orderbook: Dict[str, Any],
        price: float,
        side: str,
    ) -> tuple[List[WhaleSignal], int]:
        """Analyze one side (YES or NO) of an orderbook"""
        signals = []
        score = 0

        if not orderbook:
            return signals, score

        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        # Calculate median order size for comparison
        all_sizes = [abs(order.get("qty", 0)) for order in bids + asks]
        median_size = sorted(all_sizes)[len(all_sizes) // 2] if all_sizes else 0

        # Check for large orders
        for bid in bids:
            qty = abs(bid.get("qty", 0))
            bid_price = bid.get("price", price)
            order_value_usd = qty * bid_price

            if order_value_usd > WHALE_ACTIVITY_MIN_USD:
                signals.append(WhaleSignal(
                    market_id=market_id,
                    signal_type="large_order",
                    order_side=f"BID_{side}",
                    order_size_usd=order_value_usd,
                    order_price=bid_price,
                    confidence=80,
                    description=f"Large BID order on {side}: ${order_value_usd:,.0f}",
                    timestamp=datetime.now(),
                ))
                score = max(score, 75)

            if median_size > 0 and qty > (median_size * WHALE_SIZE_MULTIPLIER):
                signals.append(WhaleSignal(
                    market_id=market_id,
                    signal_type="unusual_size",
                    order_side=f"BID_{side}",
                    order_size_usd=order_value_usd,
                    order_price=bid_price,
                    confidence=60,
                    description=f"Order {WHALE_SIZE_MULTIPLIER}x median size on {side} BIDs",
                    timestamp=datetime.now(),
                ))
                score = max(score, 60)

        for ask in asks:
            qty = abs(ask.get("qty", 0))
            ask_price = ask.get("price", price)
            order_value_usd = qty * ask_price

            if order_value_usd > WHALE_ACTIVITY_MIN_USD:
                signals.append(WhaleSignal(
                    market_id=market_id,
                    signal_type="large_order",
                    order_side=f"ASK_{side}",
                    order_size_usd=order_value_usd,
                    order_price=ask_price,
                    confidence=80,
                    description=f"Large ASK order on {side}: ${order_value_usd:,.0f}",
                    timestamp=datetime.now(),
                ))
                score = max(score, 75)

        return signals, score

    @staticmethod
    def _check_imbalance(
        yes_orderbook: Dict[str, Any],
        no_orderbook: Dict[str, Any],
        yes_price: float,
        no_price: float,
    ) -> tuple[List[WhaleSignal], int]:
        """Check for bid-ask imbalance patterns"""
        signals = []
        score = 0

        # Calculate total bid/ask liquidity on each side
        yes_bid_qty = sum(abs(b.get("qty", 0)) for b in yes_orderbook.get("bids", []))
        yes_ask_qty = sum(abs(a.get("qty", 0)) for a in yes_orderbook.get("asks", []))

        no_bid_qty = sum(abs(b.get("qty", 0)) for b in no_orderbook.get("bids", []))
        no_ask_qty = sum(abs(a.get("qty", 0)) for a in no_orderbook.get("asks", []))

        # Check YES side imbalance
        if yes_bid_qty + yes_ask_qty > 0:
            yes_bid_pct = (yes_bid_qty / (yes_bid_qty + yes_ask_qty)) * 100
            if yes_bid_pct > WHALE_IMBALANCE_THRESHOLD or yes_bid_pct < (100 - WHALE_IMBALANCE_THRESHOLD):
                side = "BULLISH" if yes_bid_pct > 50 else "BEARISH"
                signals.append(WhaleSignal(
                    market_id="",
                    signal_type="imbalance",
                    order_side=f"YES_{side}",
                    order_size_usd=yes_bid_qty * yes_price,
                    order_price=yes_price,
                    confidence=70,
                    description=f"Orderbook imbalance on YES: {yes_bid_pct:.1f}% bids",
                    timestamp=datetime.now(),
                ))
                score = max(score, 70)

        # Check NO side imbalance
        if no_bid_qty + no_ask_qty > 0:
            no_bid_pct = (no_bid_qty / (no_bid_qty + no_ask_qty)) * 100
            if no_bid_pct > WHALE_IMBALANCE_THRESHOLD or no_bid_pct < (100 - WHALE_IMBALANCE_THRESHOLD):
                side = "BULLISH" if no_bid_pct > 50 else "BEARISH"
                signals.append(WhaleSignal(
                    market_id="",
                    signal_type="imbalance",
                    order_side=f"NO_{side}",
                    order_size_usd=no_bid_qty * no_price,
                    order_price=no_price,
                    confidence=70,
                    description=f"Orderbook imbalance on NO: {no_bid_pct:.1f}% bids",
                    timestamp=datetime.now(),
                ))
                score = max(score, 70)

        return signals, score

    @staticmethod
    def get_recent_whale_history(market_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get whale activity history for a market"""
        market_history = MarketQueries.get_market_history(market_id, hours)

        whale_events = []
        for snapshot in market_history:
            yes_ob = snapshot.get('yes_orderbook', {})
            no_ob = snapshot.get('no_orderbook', {})
            yes_price = snapshot.get('yes_price', 0.5)
            no_price = snapshot.get('no_price', 0.5)

            score, signals = WhaleDetector.analyze_orderbook(
                market_id, yes_ob, no_ob, yes_price, no_price
            )

            if signals and score > 50:
                for signal in signals:
                    whale_events.append({
                        'timestamp': snapshot.get('timestamp'),
                        'signal_type': signal.signal_type,
                        'order_side': signal.order_side,
                        'order_size_usd': signal.order_size_usd,
                        'confidence': signal.confidence,
                        'description': signal.description,
                    })

        return whale_events
