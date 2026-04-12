"""
Culture Fit Agent

Evaluates candidate alignment with company values, communication style, and leadership philosophy.
"""

from typing import Any, Dict

from ..message_bus import MessageBus
from ..orchestrator import AgentRole, MiroFishSignal
from . import HRAgent


class CultureFitAgent(HRAgent):
    """Assesses candidate cultural alignment and communication fit."""

    async def generate_proposal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> Dict[str, Any]:
        """
        Proposal based on culture alignment score from candidate data.

        Key factors:
        - culture_alignment_score: 0-1 (higher = better fit)
        - growth_indicators: signs of cultural growth
        - red_flags: any cultural concerns
        """
        culture_score = candidate_data.get("culture_alignment_score", 0.5)
        red_flags = candidate_data.get("red_flags", [])
        growth_indicators = candidate_data.get("growth_indicators", [])

        # Map score to recommendation + confidence
        if culture_score >= 0.85:
            recommendation = "STRONG_HIRE"
            confidence = min(0.92, culture_score + 0.1)
        elif culture_score >= 0.75:
            recommendation = "HIRE"
            confidence = min(0.85, culture_score + 0.05)
        elif culture_score >= 0.60:
            recommendation = "HOLD"
            confidence = culture_score
        elif culture_score >= 0.45:
            recommendation = "PASS"
            confidence = 0.40
        else:
            recommendation = "STRONG_PASS"
            confidence = 0.25

        # Adjust for red flags
        if any("culture" in flag.lower() for flag in red_flags):
            confidence = max(0.2, confidence - 0.15)
            if recommendation not in ["PASS", "STRONG_PASS"]:
                recommendation = "HOLD"

        # Boost for growth indicators
        if growth_indicators:
            confidence = min(0.95, confidence + 0.05)

        key_factors = [
            f"Culture alignment score: {culture_score:.0%}",
            "Communication and collaboration fit",
            "Values alignment and long-term integration",
        ]

        risk_flags = [flag for flag in red_flags if "culture" in flag.lower()]

        self._log_proposal(recommendation, confidence)

        return {
            "specialty": "culture_fit",
            "swarm_id": "culture_swarm",
            "recommendation": recommendation,
            "confidence": confidence,
            "summary": (
                f"Candidate shows {culture_score:.0%} cultural alignment. "
                f"Strong fit for company values and team integration."
                if culture_score >= 0.75
                else f"Candidate cultural alignment is {culture_score:.0%}. "
                f"May need cultural integration support."
            ),
            "key_factors": key_factors,
            "risk_flags": risk_flags,
            "mirofish_alignment": (
                "supports"
                if culture_score >= mirofish_signal.probability
                else "extends"
            ),
            "raw_score": culture_score,
        }

    async def generate_challenge(
        self,
        proposal: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Challenge culture fit based on specific concerns."""
        culture_score = candidate_data.get("culture_alignment_score", 0.5)
        red_flags = candidate_data.get("red_flags", [])

        if culture_score >= 0.75:
            # Challenge a strong culture fit
            challenge_type = "missing_data"
            challenge_text = (
                "Have we assessed communication style in high-pressure situations? "
                "Culture fit can shift under stress."
            )
            counter_evidence = [
                "Need stress-test interviews",
                "Team dynamics in crisis scenarios",
            ]
            confidence_impact = -0.10
        else:
            # Challenge a weak culture fit
            challenge_type = "counter_evidence"
            challenge_text = (
                "The candidate's background suggests they thrive in different "
                "work environments. How will they adapt to our pace and values?"
            )
            counter_evidence = [
                f"Previous experience in: {', '.join(candidate_data.get('skills', [])[:2])}",
                "Risk of culture clash in first 90 days",
            ]
            confidence_impact = -0.15

        return {
            "challenger_specialty": "team_dynamics",  # Different agent challenges
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
        """Respond to culture fit challenge."""
        original_confidence = original_proposal["confidence"]
        challenge_type = challenge.get("challenge_type", "unknown")

        if challenge_type == "missing_data":
            resolution = "partial"
            updated_confidence = max(0.50, original_confidence - 0.08)
            response = (
                "Valid point. We should include stress-test interview in final round. "
                "Current assessment is based on stable collaboration signals."
            )
            new_evidence = ["Will schedule leadership stress scenario interview"]
        else:
            resolution = "defended"
            updated_confidence = original_confidence
            response = (
                "Candidate's diverse background is actually a strength. "
                "They have demonstrated ability to adapt and integrate successfully."
            )
            new_evidence = [
                "Track record of successful integrations in multiple orgs",
                "Positive feedback from peer culture conversations",
            ]

        return {
            "resolution": resolution,
            "updated_recommendation": original_proposal["recommendation"],
            "updated_confidence": updated_confidence,
            "updated_summary": (
                f"Culture fit assessment updated. "
                f"Confidence now {updated_confidence:.0%}."
            ),
            "response_to_challenge": response,
            "new_evidence": new_evidence,
            "escalated": False,
        }
