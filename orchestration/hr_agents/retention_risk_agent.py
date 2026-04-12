"""
Retention Risk Agent

Evaluates retention outlook, flight risk, and stability signals.
"""

from typing import Any, Dict

from ..message_bus import MessageBus
from ..orchestrator import AgentRole, MiroFishSignal
from . import HRAgent


class RetentionRiskAgent(HRAgent):
    """Assesses retention probability, flight risk, and stability signals."""

    async def generate_proposal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> Dict[str, Any]:
        """
        Proposal based on retention risk assessment.

        Growth indicators + tenure patterns drive retention signal.
        """
        growth_indicators = candidate_data.get("growth_indicators", [])
        years_exp = candidate_data.get("years_experience", 0)
        red_flags = candidate_data.get("red_flags", [])

        # Retention logic: fewer growth moves + stable tenure = higher retention
        growth_count = len(growth_indicators)

        # Estimate tenure stability (lower growth movement = more stable)
        stability_score = 1.0 - (growth_count * 0.15)

        if stability_score >= 0.70 and years_exp >= 5:
            recommendation = "STRONG_HIRE"
            confidence = 0.88
        elif stability_score >= 0.60:
            recommendation = "HIRE"
            confidence = 0.78
        elif stability_score >= 0.45:
            recommendation = "HOLD"
            confidence = 0.58
        else:
            recommendation = "PASS"
            confidence = 0.40

        # Penalize for retention red flags
        if any("job hopping" in flag.lower() or "retention" in flag.lower() for flag in red_flags):
            confidence = max(0.20, confidence - 0.20)
            if recommendation in ["STRONG_HIRE", "HIRE"]:
                recommendation = "HOLD"

        key_factors = [
            f"Estimated stability score: {stability_score:.0%}",
            f"Career tenure stability: {years_exp} years",
            "Likelihood of 12-24 month retention",
        ]

        risk_flags = [flag for flag in red_flags if any(
            kw in flag.lower() for kw in ["job hopping", "retention", "flight risk"]
        )]

        self._log_proposal(recommendation, confidence)

        return {
            "specialty": "retention_risk",
            "swarm_id": "retention_swarm",
            "recommendation": recommendation,
            "confidence": confidence,
            "summary": (
                f"Good retention outlook. Candidate shows {stability_score:.0%} stability. "
                f"Likely to stay 24+ months."
                if confidence >= 0.75
                else f"Retention risk identified. Candidate shows {growth_count} growth moves. "
                f"Flight risk may be elevated."
            ),
            "key_factors": key_factors,
            "risk_flags": risk_flags,
            "mirofish_alignment": "supports" if stability_score >= 0.65 else "contradicts",
            "raw_score": stability_score,
        }

    async def generate_challenge(
        self,
        proposal: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Challenge retention assessment."""
        growth_indicators = candidate_data.get("growth_indicators", [])
        years_exp = candidate_data.get("years_experience", 0)

        if len(growth_indicators) <= 1 and years_exp >= 5:
            # Challenge high retention assessment
            challenge_type = "missing_data"
            challenge_text = (
                "Stability is good, but we should check for stagnation or complacency. "
                "Why haven't they grown? Are they actually engaged?"
            )
            counter_evidence = [
                "Need to assess engagement level",
                "Clarify motivations for joining us",
            ]
            confidence_impact = -0.12
        else:
            # Challenge lower retention assessment
            challenge_type = "counter_evidence"
            challenge_text = (
                "Job changes indicate ambition, not disloyalty. "
                "This role represents the growth they've been seeking."
            )
            counter_evidence = [
                "Each move was a logical career progression",
                "Compensation increase sought is modest and realistic",
            ]
            confidence_impact = +0.12

        return {
            "challenger_specialty": "growth_potential",
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
        """Respond to retention challenge."""
        original_confidence = original_proposal["confidence"]
        challenge_type = challenge.get("challenge_type", "unknown")

        if "missing_data" in challenge_type:
            resolution = "partial"
            updated_confidence = original_confidence - 0.10
            response = (
                "Fair. We should assess engagement deeply in reference calls. "
                "Stability + engagement = optimal retention."
            )
            new_evidence = [
                "Will conduct detailed engagement assessment",
                "Check previous team feedback on motivation",
            ]
        else:
            resolution = "accepted"
            updated_confidence = min(0.95, original_confidence + 0.10)
            response = (
                "Agreed. The career progression is sensible. "
                "Growth motivation is a positive signal, not a risk."
            )
            new_evidence = [
                "Clear career narrative in background",
                "Compensation expectations are reasonable",
            ]

        return {
            "resolution": resolution,
            "updated_recommendation": original_proposal["recommendation"],
            "updated_confidence": updated_confidence,
            "updated_summary": (
                f"Retention risk assessment updated. "
                f"Confidence: {updated_confidence:.0%}."
            ),
            "response_to_challenge": response,
            "new_evidence": new_evidence,
            "escalated": False,
        }
