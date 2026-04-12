"""
Technical Depth Agent

Evaluates technical competency, required skills, and experience level.
"""

from typing import Any, Dict

from ..message_bus import MessageBus
from ..orchestrator import AgentRole, MiroFishSignal
from . import HRAgent


class TechnicalDepthAgent(HRAgent):
    """Assesses technical competency, skill alignment, and experience level."""

    async def generate_proposal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> Dict[str, Any]:
        """
        Proposal based on technical match.

        Uses role_match_score as primary signal.
        """
        tech_score = candidate_data.get("role_match_score", 0.5)
        years_exp = candidate_data.get("years_experience", 0)
        skills = candidate_data.get("skills", [])
        red_flags = candidate_data.get("red_flags", [])

        # Technical fit logic
        if tech_score >= 0.85 and years_exp >= 5:
            recommendation = "STRONG_HIRE"
            confidence = 0.93
        elif tech_score >= 0.75:
            recommendation = "HIRE"
            confidence = 0.83
        elif tech_score >= 0.60:
            recommendation = "HOLD"
            confidence = 0.60
        elif tech_score >= 0.40:
            recommendation = "PASS"
            confidence = 0.40
        else:
            recommendation = "STRONG_PASS"
            confidence = 0.20

        # Penalize for technical red flags
        if any("technical" in flag.lower() or "skill" in flag.lower() for flag in red_flags):
            confidence = max(0.15, confidence - 0.25)
            if recommendation in ["STRONG_HIRE", "HIRE"]:
                recommendation = "HOLD"
            elif recommendation == "HOLD":
                recommendation = "PASS"

        key_factors = [
            f"Role match score: {tech_score:.0%}",
            f"Relevant experience: {years_exp} years",
            f"Key skills covered: {len(skills)} competencies aligned",
        ]

        risk_flags = [flag for flag in red_flags if any(
            kw in flag.lower() for kw in ["technical", "skill", "experience"]
        )]

        self._log_proposal(recommendation, confidence)

        return {
            "specialty": "technical_depth",
            "swarm_id": "skill_swarm",
            "recommendation": recommendation,
            "confidence": confidence,
            "summary": (
                f"Strong technical match ({tech_score:.0%}). "
                f"Has {years_exp}+ years relevant experience."
                if confidence >= 0.80
                else f"Technical fit is {tech_score:.0%}. "
                f"May need ramp-up time or skill development."
            ),
            "key_factors": key_factors,
            "risk_flags": risk_flags,
            "mirofish_alignment": (
                "supports"
                if tech_score >= mirofish_signal.probability
                else "contradicts"
            ),
            "raw_score": tech_score,
        }

    async def generate_challenge(
        self,
        proposal: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Challenge technical assessment."""
        tech_score = candidate_data.get("role_match_score", 0.5)
        years_exp = candidate_data.get("years_experience", 0)
        skills = candidate_data.get("skills", [])

        if tech_score >= 0.85:
            # Challenge high assessment
            challenge_type = "missing_data"
            challenge_text = (
                "High role match on paper. But have we tested depth in system design "
                "or architecture decisions? Breadth ≠ depth."
            )
            counter_evidence = [
                "Need technical architecture interview",
                "Should assess problem-solving approach",
            ]
            confidence_impact = -0.15
        else:
            # Challenge lower assessment
            challenge_type = "counter_evidence"
            challenge_text = (
                "Candidate may have learned required skills on the job. "
                "Track record of fast learning might offset low direct experience."
            )
            counter_evidence = [
                f"Demonstrated learning in: {', '.join(skills[:2]) if skills else 'TBD'}",
                "Previous roles show growth trajectory",
            ]
            confidence_impact = +0.08

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
        """Respond to technical challenge."""
        original_confidence = original_proposal["confidence"]
        challenge_type = challenge.get("challenge_type", "unknown")

        if "missing_data" in challenge_type:
            resolution = "partial"
            updated_confidence = original_confidence - 0.10
            response = (
                "Good catch. We will include architectural deep-dive in technical interview. "
                "Current assessment based on direct skill alignment."
            )
            new_evidence = [
                "Will conduct system design interview",
                "Request code review samples for assessment",
            ]
        else:
            resolution = "accepted"
            updated_confidence = min(0.95, original_confidence + 0.06)
            response = (
                "Agreed. The candidate has consistently picked up new technologies. "
                "Learning velocity is a strong indicator here."
            )
            new_evidence = [
                "5 instances of learning new framework in 3 years",
                "Successfully led technical migration project",
            ]

        return {
            "resolution": resolution,
            "updated_recommendation": original_proposal["recommendation"],
            "updated_confidence": updated_confidence,
            "updated_summary": (
                f"Technical assessment updated. "
                f"Confidence: {updated_confidence:.0%}."
            ),
            "response_to_challenge": response,
            "new_evidence": new_evidence,
            "escalated": False,
        }
