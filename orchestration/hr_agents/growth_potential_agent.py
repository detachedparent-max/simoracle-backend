"""
Growth Potential Agent

Evaluates candidate's growth trajectory, promotability, and leadership ceiling.
"""

from typing import Any, Dict

from ..message_bus import MessageBus
from ..orchestrator import AgentRole, MiroFishSignal
from . import HRAgent


class GrowthPotentialAgent(HRAgent):
    """Assesses growth trajectory, promotability timeline, and leadership potential."""

    async def generate_proposal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> Dict[str, Any]:
        """
        Proposal based on growth indicators and potential.

        Growth indicators drive the assessment.
        """
        growth_indicators = candidate_data.get("growth_indicators", [])
        years_exp = candidate_data.get("years_experience", 0)
        red_flags = candidate_data.get("red_flags", [])

        # Growth logic
        growth_count = len(growth_indicators)

        if growth_count >= 3 and years_exp >= 5:
            recommendation = "STRONG_HIRE"
            confidence = 0.91
        elif growth_count >= 2 and years_exp >= 3:
            recommendation = "HIRE"
            confidence = 0.82
        elif growth_count >= 1 or years_exp >= 5:
            recommendation = "HOLD"
            confidence = 0.65
        else:
            recommendation = "PASS"
            confidence = 0.45

        # Penalize for stagnation red flags
        if any("stagnation" in flag.lower() or "growth" in flag.lower() for flag in red_flags):
            confidence = max(0.25, confidence - 0.20)
            if recommendation in ["STRONG_HIRE", "HIRE"]:
                recommendation = "HOLD"

        key_factors = [
            f"Growth indicators identified: {growth_count}",
            f"Career trajectory over {years_exp} years",
            "Leadership and promotability potential",
        ]

        risk_flags = [flag for flag in red_flags if "growth" in flag.lower() or "stagnation" in flag.lower()]

        self._log_proposal(recommendation, confidence)

        return {
            "specialty": "growth_potential",
            "swarm_id": "skill_swarm",
            "recommendation": recommendation,
            "confidence": confidence,
            "summary": (
                f"Strong growth trajectory with {growth_count} positive indicators. "
                f"High potential for development and leadership."
                if confidence >= 0.80
                else f"Moderate growth indicators ({growth_count} identified). "
                f"May need clear development path to unlock potential."
            ),
            "key_factors": key_factors,
            "risk_flags": risk_flags,
            "mirofish_alignment": (
                "supports" if growth_count >= 2 else "extends"
            ),
            "raw_score": min(1.0, 0.4 + (growth_count * 0.2) + (years_exp / 20)),
        }

    async def generate_challenge(
        self,
        proposal: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Challenge growth assessment."""
        growth_indicators = candidate_data.get("growth_indicators", [])
        years_exp = candidate_data.get("years_experience", 0)

        if len(growth_indicators) >= 3:
            # Challenge high growth assessment
            challenge_type = "assumption"
            challenge_text = (
                "Fast growth trajectory is good, but will it sustain in our environment? "
                "Past growth may reflect stepping-stone mentality."
            )
            counter_evidence = [
                "Each role change was self-initiated",
                "Average tenure: 2 years per role",
                "Could indicate flight risk",
            ]
            confidence_impact = -0.15
        else:
            # Challenge lower growth assessment
            challenge_type = "counter_evidence"
            challenge_text = (
                "Candidate may have been constrained by role, not by potential. "
                "They're now seeking growth opportunity in our role."
            )
            counter_evidence = [
                f"{years_exp}+ years in stable roles is not stagnation",
                "New role represents growth step forward",
            ]
            confidence_impact = +0.10

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
        """Respond to growth potential challenge."""
        original_confidence = original_proposal["confidence"]
        challenge_type = challenge.get("challenge_type", "unknown")

        if "assumption" in challenge_type:
            resolution = "partial"
            updated_confidence = original_confidence - 0.08
            response = (
                "Valid concern. We should discuss 3-year growth plan and "
                "retention incentives as part of offer negotiation."
            )
            new_evidence = [
                "Will include career development path in offer",
                "Leadership mentorship program available",
            ]
        else:
            resolution = "defended"
            updated_confidence = original_confidence
            response = (
                "Agreed. The candidate has been effective in stable roles. "
                "They're seeking growth, not running from problems."
            )
            new_evidence = [
                "Positive references from previous managers",
                "This role represents meaningful growth opportunity",
            ]

        return {
            "resolution": resolution,
            "updated_recommendation": original_proposal["recommendation"],
            "updated_confidence": updated_confidence,
            "updated_summary": (
                f"Growth potential assessment updated. "
                f"Confidence: {updated_confidence:.0%}."
            ),
            "response_to_challenge": response,
            "new_evidence": new_evidence,
            "escalated": False,
        }
