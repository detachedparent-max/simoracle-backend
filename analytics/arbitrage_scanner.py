"""
Arbitrage scanner - detects cross-platform price gaps
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from config import ARBITRAGE_MIN_SPREAD_PCT, ARBITRAGE_MIN_LIQUIDITY_USD


@dataclass
class ArbitrageOpportunity:
    market_id: str
    platform1: str
    platform2: str
    price1: float
    price2: float
    spread_pct: float
    liquidity1_usd: float
    liquidity2_usd: float
    action: str  # 'BUY_PLATFORM1_SELL_PLATFORM2' or vice versa
    estimated_profit_usd: float
    confidence: int
    timestamp: datetime


class ArbitrageScanner:
    """Detects profitable price gaps across prediction platforms"""

    @staticmethod
    def scan_platforms(
        market_id: str,
        kalshi_price: float,
        kalshi_liquidity: float,
        manifesto_price: Optional[float] = None,
        manifesto_liquidity: Optional[float] = None,
        polymarket_price: Optional[float] = None,
        polymarket_liquidity: Optional[float] = None,
    ) -> List[ArbitrageOpportunity]:
        """
        Scan for arbitrage opportunities across platforms
        Returns: list of profitable spreads
        """
        opportunities = []

        # Check Kalshi vs Manifesto
        if manifesto_price is not None and manifesto_liquidity is not None:
            if kalshi_liquidity >= ARBITRAGE_MIN_LIQUIDITY_USD and manifesto_liquidity >= ARBITRAGE_MIN_LIQUIDITY_USD:
                opp = ArbitrageScanner._check_pair(
                    market_id,
                    "Kalshi", kalshi_price, kalshi_liquidity,
                    "Manifesto", manifesto_price, manifesto_liquidity,
                )
                if opp:
                    opportunities.append(opp)

        # Check Kalshi vs Polymarket
        if polymarket_price is not None and polymarket_liquidity is not None:
            if kalshi_liquidity >= ARBITRAGE_MIN_LIQUIDITY_USD and polymarket_liquidity >= ARBITRAGE_MIN_LIQUIDITY_USD:
                opp = ArbitrageScanner._check_pair(
                    market_id,
                    "Kalshi", kalshi_price, kalshi_liquidity,
                    "Polymarket", polymarket_price, polymarket_liquidity,
                )
                if opp:
                    opportunities.append(opp)

        # Check Manifesto vs Polymarket
        if manifesto_price is not None and polymarket_price is not None:
            if manifesto_liquidity >= ARBITRAGE_MIN_LIQUIDITY_USD and polymarket_liquidity >= ARBITRAGE_MIN_LIQUIDITY_USD:
                opp = ArbitrageScanner._check_pair(
                    market_id,
                    "Manifesto", manifesto_price, manifesto_liquidity,
                    "Polymarket", polymarket_price, polymarket_liquidity,
                )
                if opp:
                    opportunities.append(opp)

        return opportunities

    @staticmethod
    def _check_pair(
        market_id: str,
        platform1: str,
        price1: float,
        liquidity1: float,
        platform2: str,
        price2: float,
        liquidity2: float,
    ) -> Optional[ArbitrageOpportunity]:
        """Check if a price pair has exploitable spread"""

        # Calculate spread as percentage
        spread_pct = abs((price1 - price2) / ((price1 + price2) / 2)) * 100

        if spread_pct < ARBITRAGE_MIN_SPREAD_PCT:
            return None  # Spread too small

        # Determine which is cheaper
        if price1 < price2:
            cheap_platform = platform1
            expensive_platform = platform2
            cheap_price = price1
            expensive_price = price2
            cheap_liquidity = liquidity1
            expensive_liquidity = liquidity2
            action = f"BUY_{platform1.upper()}_SELL_{platform2.upper()}"
        else:
            cheap_platform = platform2
            expensive_platform = platform1
            cheap_price = price2
            expensive_price = price1
            cheap_liquidity = liquidity2
            expensive_liquidity = liquidity1
            action = f"BUY_{platform2.upper()}_SELL_{platform1.upper()}"

        # Estimate profit (per contract)
        profit_per_contract = expensive_price - cheap_price

        # Assume we can trade 100 contracts (conservative)
        tradeable_volume = min(cheap_liquidity, expensive_liquidity) / ((cheap_price + expensive_price) / 2)
        tradeable_contracts = min(100, int(tradeable_volume))
        estimated_profit = profit_per_contract * tradeable_contracts

        # Confidence based on liquidity and spread size
        confidence = min(95, 50 + int(spread_pct * 3))

        return ArbitrageOpportunity(
            market_id=market_id,
            platform1=platform1,
            platform2=platform2,
            price1=price1,
            price2=price2,
            spread_pct=spread_pct,
            liquidity1_usd=liquidity1,
            liquidity2_usd=liquidity2,
            action=action,
            estimated_profit_usd=estimated_profit,
            confidence=confidence,
            timestamp=datetime.now(),
        )

    @staticmethod
    def aggregate_opportunities(
        opportunities: List[ArbitrageOpportunity],
        min_confidence: int = 60,
    ) -> List[Dict[str, Any]]:
        """Format opportunities for API response"""
        filtered = [opp for opp in opportunities if opp.confidence >= min_confidence]

        # Sort by estimated profit descending
        filtered.sort(key=lambda x: x.estimated_profit_usd, reverse=True)

        return [
            {
                'market_id': opp.market_id,
                'platform1': opp.platform1,
                'platform2': opp.platform2,
                'price1': opp.price1,
                'price2': opp.price2,
                'spread_pct': round(opp.spread_pct, 2),
                'liquidity1_usd': round(opp.liquidity1_usd, 2),
                'liquidity2_usd': round(opp.liquidity2_usd, 2),
                'action': opp.action,
                'estimated_profit_usd': round(opp.estimated_profit_usd, 2),
                'confidence': opp.confidence,
                'timestamp': opp.timestamp.isoformat(),
            }
            for opp in filtered
        ]
