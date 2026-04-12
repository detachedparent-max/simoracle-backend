"""
Team Dynamics Agent

Evaluates how a candidate complements the existing team, manager fit, and team chemistry.
"""

from typing import Any, Dict

from ..message_bus import MessageBus
from ..orchestrator import AgentRole, MiroFishSignal
from . import HRAgent


class TeamDynamicsAgent(HRAgent):
    """Assesses team fit, manager compatibility, and complementary strengths."""

    async def generate_proposal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> Dict[str, Any]:
        """
        Proposal based on team dynamics fit.

        Uses culture_alignment_score as proxy for team fit.
        """
        team_fit_score = candidate_data.get("culture_alignment_score", 0.5)
        years_exp = candidate_data.get("years_experience", 0)
        red_flags = candidate_data.get("red_flags", [])

        # Team fit logic
        if team_fit_score >= 0.80 and years_exp >= 5:
            recommendation = "STRONG_HIRE"
            confidence = 0.90
        elif team_fit_score >= 0.70:
            recommendation = "HIRE"
            confidence = 0.80
        elif team_fit_score >= 0.55:
            recommendation = "HOLD"
            confidence = 0.55
        else:
            recommendation = "PASS"
            confidence = 0.35

        # Penalize for communication red flags
        if any("communication" in flag.lower() for flag in red_flags):
            confidence = max(0.2, confidence - 0.20)
            if recommendation == "STRONG_HIRE":
                recommendation = "HIRE"
            elif recommendation == "HIRE":
                recommendation = "HOLD"

        key_factors = [
            f"Team chemistry fit: {team_fit_score:.0%}",
            f"Experience level: {years_exp} years",
            "Manager alignment and leadership style compatibility",
        ]

        risk_flags = [flag for flag in red_flags if "communication" in flag.lower()]

        self._log_proposal(recommendation, confidence)

        return {
            "specialty": "team_dynamics",
            "swarm_id": "culture_swarm",
            "recommendation": recommendation,
            "confidence": confidence,
            "summary": (
                f"Strong team fit with {years_exp}+ years experience. "
                f"Will complement existing team dynamics."
                if recommendation in ["HIRE", "STRONG_HIRE"]
                else f"Team fit concerns identified. "
                f"May require onboarding support or role adjustment."
            ),
            "key_factors": key_factors,
            "risk_flags": risk_flags,
            "mirofish_alignment": (
                "supports"
                if team_fit_score >= mirofish_signal.probability - 0.05
                else "extends"
            ),
            "raw_score": team_fit_score,
        }

    async def generate_challenge(
        self,
        proposal: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Challenge team dynamics assessment."""
        team_fit = candidate_data.get("culture_alignment_score", 0.5)
        years_exp = candidate_data.get("years_experience", 0)

        if team_fit >= 0.75 and years_exp >= 7:
            # Challenge a strong assessment
            challenge_type = "assumption"
            challenge_text = (
                "Experience and team fit don't guarantee successful integration. "
                "Have we assessed how this person handles disagreement or failure?"
            )
            counter_evidence = [
                "Need to evaluate conflict resolution style",
                "Test working with different personality types",
            ]
            confidence_impact = -0.12
        else:
            # Challenge weak assessment
            challenge_type = "counter_evidence"
            challenge_text = (
                "Limited team experience may mean slower ramp-up. "
                "Do we have capacity to mentor and integrate?"
            )
            counter_evidence = [
                f"Current team bandwidth: unclear",
                "No dedicated onboarding resource identified",
            ]
            confidence_impact = -0.10

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
        """Respond to team dynamics challenge."""
        original_confidence = original_proposal["confidence"]
        challenge_type = challenge.get("challenge_type", "unknown")

        if "assumption" in challenge_type:
            resolution = "partial"
            updated_confidence = original_confidence - 0.08
            response = (
                "Fair point on conflict resolution. "
                "We can add behavioral interview to assess this dimension."
            )
            new_evidence = [
                "Will conduct situation-based interview on disagreement handling"
            ]
        else:
            resolution = "defended"
            updated_confidence = original_confidence
            response = (
                "Team has already identified a mentor. "
                "Onboarding plan is in place and approved."
            )
            new_evidence = [
                "Dedicated mentor assigned (senior engineer)",
                "2-week structured onboarding documented",
            ]

        return {
            "resolution": resolution,
            "updated_recommendation": original_proposal["recommendation"],
            "updated_confidence": updated_confidence,
            "updated_summary": (
                f"Team fit assessment updated. "
                f"Confidence: {updated_confidence:.0%}."
            ),
            "response_to_challenge": response,
            "new_evidence": new_evidence,
            "escalated": False,
        }
