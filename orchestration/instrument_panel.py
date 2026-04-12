"""
Instrument Panel

Formats AgentBoard results into executive-facing reports.
Produces Bloomberg-style output with reasoning chain, not raw predictions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .debate_protocol import BoardSynthesisContent
from .message_bus import Message
from .transcript_builder import TranscriptBuilder

logger = logging.getLogger(__name__)


class InstrumentPanel:
    """Formats board synthesis and transcript into executive report."""

    def __init__(
        self,
        synthesis: BoardSynthesisContent,
        transcript_messages: List[Message],
        candidate_data: Dict[str, Any],
    ):
        """
        Initialize instrument panel.

        Args:
            synthesis: BoardSynthesisContent from board debate
            transcript_messages: Full message transcript
            candidate_data: Original candidate information
        """
        self.synthesis = synthesis
        self.transcript_builder = TranscriptBuilder(transcript_messages)
        self.candidate_data = candidate_data
        self.generated_at = datetime.now()

    def get_executive_summary(self) -> Dict[str, Any]:
        """
        High-level decision summary for executives.

        Returns:
            {
                "decision": str,
                "confidence": float,
                "executive_summary": str,
                "recommendation": str,
                "key_drivers": [str],
                "critical_risks": [str],
                "recommended_next_steps": [str],
            }
        """
        recommendation = self.synthesis.get("final_recommendation", "UNKNOWN")
        confidence = self.synthesis.get("final_confidence", 0)

        # Map recommendation to decision and next steps
        decision_map = {
            "STRONG_HIRE": {
                "decision": "HIRE",
                "tone": "Strong positive signal. Board unanimously recommends.",
                "next_steps": [
                    "Extend offer",
                    "Schedule team introductions",
                    "Conduct final background check",
                ],
            },
            "HIRE": {
                "decision": "HIRE",
                "tone": "Positive signal. Board recommends with normal diligence.",
                "next_steps": [
                    "Prepare offer",
                    "Address identified concerns",
                    "Team feedback meeting",
                ],
            },
            "HOLD": {
                "decision": "HOLD",
                "tone": "Mixed signals. Recommend further evaluation.",
                "next_steps": [
                    "Clarify ambiguous areas",
                    "Get additional references",
                    "Role-specific technical assessment",
                ],
            },
            "PASS": {
                "decision": "PASS",
                "tone": "Negative signal. Board recommends rejection.",
                "next_steps": [
                    "Send polite decline",
                    "Offer future opportunity",
                    "Document decision rationale",
                ],
            },
            "STRONG_PASS": {
                "decision": "STRONG_PASS",
                "tone": "Strong negative signal. Board unanimously recommends rejection.",
                "next_steps": [
                    "Immediate decline",
                    "Document critical blockers",
                    "Note for future reference",
                ],
            },
        }

        decision_info = decision_map.get(
            recommendation,
            {
                "decision": "UNKNOWN",
                "tone": "Unable to determine.",
                "next_steps": ["Escalate to decision-maker"],
            },
        )

        return {
            "decision": decision_info["decision"],
            "confidence": confidence,
            "executive_summary": decision_info["tone"],
            "recommendation": recommendation,
            "key_drivers": self.synthesis.get("key_drivers", []),
            "critical_risks": self.synthesis.get("critical_risks", []),
            "recommended_next_steps": decision_info["next_steps"],
        }

    def get_reasoning_chain(self) -> Dict[str, Any]:
        """
        Detailed reasoning path for the decision.

        Shows:
        - What each swarm thought
        - Where they disagreed
        - How board resolved differences
        - Key insight that drove final recommendation

        Returns:
            {
                "phase_1_initial_signals": {...},
                "phase_2_debate": {...},
                "phase_3_tensions": {...},
                "phase_4_synthesis": {...},
            }
        """
        synthesis = self.synthesis
        swarm_inputs = synthesis.get("swarm_inputs", {})

        # swarm_inputs can be either dict (new format) or just recommendation string
        swarm_recs = {}
        for swarm_id, val in swarm_inputs.items():
            if isinstance(val, dict):
                swarm_recs[swarm_id] = val.get("recommendation", "N/A")
            else:
                # val is a string recommendation
                swarm_recs[swarm_id] = val

        return {
            "phase_1_initial_signals": {
                "description": "MiroFish oracle + initial agent proposals",
                "swarm_recommendations": swarm_recs,
            },
            "phase_2_debate": {
                "description": "Agents challenge each other's logic",
                "key_challenge_patterns": self._extract_challenge_patterns(),
            },
            "phase_3_tensions": {
                "description": "Cross-domain disagreements highlighted",
                "tensions": synthesis.get("cross_domain_tensions", []),
                "resolution_method": "Majority voting with confidence weighting",
            },
            "phase_4_synthesis": {
                "description": "Board final recommendation",
                "rationale": synthesis.get("board_rationale", ""),
                "confidence_evolution": self._get_confidence_timeline(),
            },
        }

    def get_detailed_report(self) -> Dict[str, Any]:
        """
        Complete report with all reasoning, debate record, and metrics.

        Returns:
            {
                "metadata": {...},
                "executive_summary": {...},
                "reasoning_chain": {...},
                "debate_summary": {...},
                "transcript": str,
                "metrics": {...},
            }
        """
        return {
            "metadata": {
                "candidate": self.candidate_data.get("name", "Unknown"),
                "generated_at": self.generated_at.isoformat(),
                "experience_level": f"{self.candidate_data.get('years_experience', 0)} years",
                "role_match": f"{self.candidate_data.get('role_match_score', 0):.0%}",
            },
            "executive_summary": self.get_executive_summary(),
            "reasoning_chain": self.get_reasoning_chain(),
            "debate_summary": self.transcript_builder.summary_stats(),
            "transcript": self.transcript_builder.get_formatted_text(),
            "metrics": self._get_metrics(),
        }

    def get_candidate_scorecard(self) -> Dict[str, Any]:
        """
        Scorecard-style view of candidate across domains.

        Returns:
            {
                "culture_fit": {...},
                "technical_depth": {...},
                "retention_risk": {...},
                "overall": {...},
            }
        """
        swarm_inputs = self.synthesis.get("swarm_inputs", {})

        def get_swarm_card(swarm_id: str):
            """Extract scorecard from swarm input (may be dict or string)."""
            val = swarm_inputs.get(swarm_id, {})
            if isinstance(val, dict):
                return {
                    "elected_agent": val.get("elected_specialty", "N/A"),
                    "recommendation": val.get("recommendation", "N/A"),
                    "confidence": val.get("confidence", 0),
                    "summary": val.get("summary", ""),
                }
            else:
                # Just a recommendation string
                return {
                    "elected_agent": "N/A",
                    "recommendation": val,
                    "confidence": 0,
                    "summary": "",
                }

        return {
            "culture_fit": get_swarm_card("culture_swarm"),
            "technical_depth": get_swarm_card("skill_swarm"),
            "retention_risk": get_swarm_card("retention_swarm"),
            "overall": {
                "final_recommendation": self.synthesis.get("final_recommendation"),
                "final_confidence": self.synthesis.get("final_confidence", 0),
                "escalation_count": self.synthesis.get("escalation_count", 0),
            },
        }

    def _extract_challenge_patterns(self) -> List[str]:
        """Extract common challenge types from debate."""
        challenge_patterns = []
        for thread in self.transcript_builder.threads.values():
            for challenge in thread.challenges:
                challenge_type = challenge.content.get("challenge_type", "unknown")
                if challenge_type not in challenge_patterns:
                    challenge_patterns.append(challenge_type)
        return challenge_patterns

    def _get_confidence_timeline(self) -> List[Dict[str, Any]]:
        """Extract confidence progression through debate phases."""
        timeline = []
        trajectory = self.synthesis.get("confidence_trajectory", [])
        for phase_data in trajectory:
            timeline.append(
                {
                    "phase": phase_data.get("phase", "unknown"),
                    "confidence": phase_data.get("confidence", 0),
                }
            )
        return timeline

    def _get_metrics(self) -> Dict[str, Any]:
        """Calculate metrics about the debate."""
        stats = self.transcript_builder.summary_stats()
        synthesis = self.synthesis

        return {
            "debate_depth": self._estimate_debate_depth(stats),
            "agent_agreement": self._calculate_agent_agreement(),
            "confidence_change": self._calculate_confidence_change(),
            "escalation_required": synthesis.get("escalation_count", 0) > 0,
            "total_messages_exchanged": stats["total_messages"],
            "phases_executed": stats["debate_phases"],
        }

    def _estimate_debate_depth(self, stats: Dict[str, Any]) -> str:
        """Estimate debate depth based on message counts."""
        challenge_count = stats["challenge_count"]
        if challenge_count == 0:
            return "MINIMAL"
        elif stats["reconciliation_count"] == 0:
            return "LIGHT"
        else:
            return "FULL"

    def _calculate_agent_agreement(self) -> float:
        """Calculate how much agents agreed (0-1)."""
        swarm_inputs = self.synthesis.get("swarm_inputs", {})
        if not swarm_inputs:
            return 1.0

        recommendations = []
        for val in swarm_inputs.values():
            if isinstance(val, dict):
                recommendations.append(val.get("recommendation", ""))
            else:
                # val is a string recommendation
                recommendations.append(val)

        unique_recommendations = len(set(recommendations))
        total_swarms = len(recommendations)

        # If all swarms agree: 1.0
        # If split: 0.5
        return 1.0 - (unique_recommendations - 1) / max(total_swarms - 1, 1)

    def _calculate_confidence_change(self) -> float:
        """Calculate total confidence shift through debate phases."""
        trajectory = self.synthesis.get("confidence_trajectory", [])
        if len(trajectory) < 2:
            return 0.0

        initial = trajectory[0].get("confidence", 0)
        final = trajectory[-1].get("confidence", 0)
        return final - initial

    def to_json(self) -> Dict[str, Any]:
        """Serialize entire panel to JSON-safe dict."""
        return self.get_detailed_report()
