"""
Sample report generator for instant product proof
No authentication required - demonstrates core prediction capability
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SamplePrediction(BaseModel):
    """Single prediction in sample report"""
    event: str
    oracle: str
    probability: float
    action: str  # BUY_YES or BUY_NO
    reasoning: str
    catalysts: List[str]
    confidence: int  # 1-10
    generated_at: str


class SampleReport(BaseModel):
    """Complete sample report response"""
    report_id: str
    predictions: List[SamplePrediction]
    report_generated_at: str
    disclaimer: str


def generate_sample_report() -> Dict[str, Any]:
    """
    Generate a realistic sample report with 5-6 predictions across different oracles.
    Uses hard-coded examples to demonstrate prediction capabilities without LLM calls.
    """
    now = datetime.utcnow().isoformat() + "Z"
    report_id = f"sample_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    predictions = [
        {
            "event": "Will NOAA forecast rain in NYC on 2026-04-05?",
            "oracle": "weather",
            "probability": 0.72,
            "action": "BUY_YES",
            "reasoning": "70% chance of precipitation based on NOAA GFS model. Low-pressure system moving northeast with warm, moist air from Atlantic. GFS, NAM, and HRRR models show 70-75% agreement on precipitation. Historical accuracy for this setup is 74% in spring.",
            "catalysts": [
                "Low pressure system centered over Ohio moving northeast",
                "90% model agreement (GFS, NAM, HRRR)",
                "Warm moist air mass from Atlantic",
                "Historical 74% accuracy for this pattern in April"
            ],
            "confidence": 8,
            "generated_at": now,
        },
        {
            "event": "Will Donald Trump win New Hampshire primary on 2024-01-23?",
            "oracle": "politics",
            "probability": 0.68,
            "action": "BUY_YES",
            "reasoning": "Trump leads 6 of 7 most recent NH polls. Average polling lead: +8.2 pts. Haley consolidating moderate vote but still trails by 7-10 pts. Historical polling accuracy in NH primaries: 89% for final week predictions.",
            "catalysts": [
                "Trump leads 6/7 recent polls (avg +8.2 pts)",
                "Haley moderates split opposition",
                "Historical polling accuracy 89% for final week",
                "Strong endorsement from Ron DeSantis voters"
            ],
            "confidence": 8,
            "generated_at": now,
        },
        {
            "event": "Will Tesla stock close above $185 on 2026-04-10?",
            "oracle": "equity",
            "probability": 0.55,
            "action": "BUY_YES",
            "reasoning": "Current price $182.45. Neutral momentum. Recent earnings beat expectations on margins. Fed policy shift supports tech valuations. Analyst consensus target: $185-195 range. Volatility 35% annualized—standard for mega-cap tech.",
            "catalysts": [
                "Q1 earnings beat on auto margin expansion",
                "Fed rate cut cycle expectation improving",
                "Analyst consensus: $185-195 price target",
                "Technical support at $180"
            ],
            "confidence": 6,
            "generated_at": now,
        },
        {
            "event": "Will Kansas City Chiefs win Super Bowl LVIII?",
            "oracle": "sports",
            "probability": 0.38,
            "action": "BUY_NO",
            "reasoning": "Chiefs currently 3rd favorite (implied 25% odds from betting markets). Strong defense (7th NFL rank) but offense regressed post-injury. San Francisco 49ers and Buffalo Bills have superior offenses. Super Bowl performance heavily correlated with offensive firepower and playoff experience.",
            "catalysts": [
                "Chiefs offensive line injuries (Thuney, Creed Humphrey)",
                "49ers offense ranked #2 vs Chiefs #18",
                "Patrick Mahomes playoff record: 9-6 in last 15 games",
                "Home field advantage (neutral sites in playoffs)"
            ],
            "confidence": 7,
            "generated_at": now,
        },
        {
            "event": "Will Bitcoin close above $70,000 on 2026-04-06?",
            "oracle": "crypto",
            "probability": 0.62,
            "action": "BUY_YES",
            "reasoning": "Bitcoin currently $71,200. Technical resistance at $75K. Institutional flows positive (ETF inflows $500M week). Macro tailwinds from Fed pivot. Volatility 65% annualized—elevated but manageable. Probability slightly below current price due to mean-reversion expectations.",
            "catalysts": [
                "Bitcoin ETF inflows: $500M+ per week",
                "Fed rate cut cycle expected Q3 2026",
                "Technical support at $68K (previous resistance)",
                "Macro correlation with 2Y yields declining"
            ],
            "confidence": 7,
            "generated_at": now,
        },
        {
            "event": "Will Fed raise rates in June 2026 FOMC meeting?",
            "oracle": "macro",
            "probability": 0.18,
            "action": "BUY_NO",
            "reasoning": "Current PCE inflation: 2.8%. Core PCE: 3.2%. Fed funds rate: 5.25-5.50%. Futures market pricing ~15% odds of hike. Powell guidance: 'data-dependent but patient.' Unemployment 3.9%. Consensus: hold steady through Q2, pivot to cuts Q3.",
            "catalysts": [
                "PCE inflation cooling (3.2% vs 3.5% last quarter)",
                "Fed funds futures: 15% hike odds",
                "Powell guidance: patient and data-dependent",
                "Unemployment stable at 3.9%"
            ],
            "confidence": 8,
            "generated_at": now,
        },
    ]

    return {
        "report_id": report_id,
        "predictions": predictions,
        "report_generated_at": now,
        "disclaimer": "Predictions are for informational purposes only and should not be considered investment advice. Past performance does not guarantee future results. All predictions involve inherent risks and may not be accurate. SimOracle makes no guarantees about prediction accuracy, market performance, or trading outcomes. Users should conduct their own research and consult professional advisors before making financial decisions based on these predictions.",
    }
