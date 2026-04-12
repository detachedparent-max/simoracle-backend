"""
Market Competitiveness Agent

Evaluates compensation realism, market demand for skills, and poaching risk.
"""

from typing import Any, Dict

from ..message_bus import MessageBus
from ..orchestrator import AgentRole, MiroFishSignal
from . import HRAgent


class MarketCompAgent(HRAgent):
    """Assesses market compensation realism, skill scarcity, and competitive risk."""

    async def generate_proposal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> Dict[str, Any]:
        """
        Proposal based on compensation and market positioning.

        Compares compensation_ask to market_rate.
        """
        compensation_ask = candidate_data.get("compensation_ask", 100000)
        market_rate = candidate_data.get("market_rate", 100000)
        skills = candidate_data.get("skills", [])
        years_exp = candidate_data.get("years_experience", 0)
        red_flags = candidate_data.get("red_flags", [])

        # Compensation logic
        if market_rate == 0:
            market_rate = 100000  # Default fallback
        comp_ratio = compensation_ask / market_rate

        if comp_ratio <= 0.95:
            # Below market = good deal
            recommendation = "STRONG_HIRE"
            confidence = 0.92
        elif comp_ratio <= 1.05:
            # Within 5% of market = reasonable
            recommendation = "HIRE"
            confidence = 0.85
        elif comp_ratio <= 1.15:
            # 5-15% above market = negotiable
            recommendation = "HOLD"
            confidence = 0.65
        elif comp_ratio <= 1.25:
            # 15-25% above market = high risk
            recommendation = "PASS"
            confidence = 0.40
        else:
            # 25%+ above market = unrealistic
            recommendation = "STRONG_PASS"
            confidence = 0.15

        # Boost for scarce skills
        scarce_skills = [s for s in skills if any(
            kw in s.lower() for kw in ["ml", "ai", "distributed systems", "rust", "go"]
        )]
        if scarce_skills and comp_ratio <= 1.10:
            confidence = min(0.95, confidence + 0.08)

        # Penalize for compensation red flags
        if any("compensation" in flag.lower() or "salary" in flag.lower() for flag in red_flags):
            confidence = max(0.15, confidence - 0.10)

        key_factors = [
            f"Compensation ask: ${compensation_ask:,}",
            f"Market rate: ${market_rate:,}",
            f"Ratio: {comp_ratio:.0%} of market",
        ]

        risk_flags = [flag for flag in red_flags if any(
            kw in flag.lower() for kw in ["compensation", "salary", "poaching"]
        )]

        self._log_proposal(recommendation, confidence)

        return {
            "specialty": "market_competitiveness",
            "swarm_id": "retention_swarm",
            "recommendation": recommendation,
            "confidence": confidence,
            "summary": (
                f"Competitive compensation. "
                f"Asking {comp_ratio:.0%} of market rate (${compensation_ask:,})."
                if comp_ratio <= 1.10
                else f"Compensation above market expectations. "
                f"Asking ${compensation_ask:,} vs. {comp_ratio:.0%} market baseline."
            ),
            "key_factors": key_factors,
            "risk_flags": risk_flags,
            "mirofish_alignment": (
                "supports" if comp_ratio <= 1.05 else "contradicts"
            ),
            "raw_score": max(0.0, 1.0 - min(0.5, (comp_ratio - 1.0) * 2)),
        }

    async def generate_challenge(
        self,
        proposal: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Challenge market assessment."""
        compensation_ask = candidate_data.get("compensation_ask", 100000)
        market_rate = candidate_data.get("market_rate", 100000)
        skills = candidate_data.get("skills", [])

        if market_rate > 0:
            comp_ratio = compensation_ask / market_rate
        else:
            comp_ratio = 1.0

        if comp_ratio <= 0.95:
            # Challenge below-market offer
            challenge_type = "assumption"
            challenge_text = (
                "Below-market offer is attractive short-term but may signal "
                "we don't value this candidate. Retention risk if market improves."
            )
            counter_evidence = [
                "Candidate may feel undervalued",
                "Risk of losing to competitor offer",
            ]
            confidence_impact = -0.10
        else:
            # Challenge above-market ask
            challenge_type = "counter_evidence"
            challenge_text = (
                f"Candidate's skills ({', '.join(skills[:2])}) are in demand. "
                f"Above-market ask is justified by scarcity."
            )
            counter_evidence = [
                f"Market for {skills[0] if skills else 'needed skills'} is tight",
                "Offer below ask will invite counter-offers",
            ]
            confidence_impact = +0.08

        return {
            "challenger_specialty": "retention_risk",
            "challenge_type": challenge_type,
            "challenge_text": challenge_text,
            "counter_evidence": counter_evidence,
            "confidence_impact": confidence_impact,
        }

    async def generate_reconciliation(
        self,
        challenge: Dict[str, Any],
        original_proposal: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Respond to market challenge."""
        original_confidence = original_proposal["confidence"]
        challenge_type = challenge.get("challenge_type", "unknown")

        if "assumption" in challenge_type:
            resolution = "accepted"
            updated_confidence = original_confidence - 0.05
            response = (
                "Fair point. We should ensure total comp package "
                "(equity, benefits, growth) is competitive."
            )
            new_evidence = [
                "Will increase base offer to market rate",
                "Add equity incentive for retention",
            ]
        else:
            resolution = "defended"
            updated_confidence = original_confidence
            response = (
                "Agreed. The candidate's skillset is scarce in market. "
                "Asking price is justified by market dynamics."
            )
            new_evidence = [
                "Recent market analysis confirms scarcity premium",
                "Similar profiles commanding 10-20% premium elsewhere",
            ]

        return {
            "resolution": resolution,
            "updated_recommendation": original_proposal["recommendation"],
            "updated_confidence": updated_confidence,
            "updated_summary": (
                f"Market assessment updated. "
                f"Confidence: {updated_confidence:.0%}."
            ),
            "response_to_challenge": response,
            "new_evidence": new_evidence,
            "escalated": False,
        }
