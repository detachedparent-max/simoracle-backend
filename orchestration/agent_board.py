"""
Agent Board & SubSwarm

Orchestrates multi-agent debates and board synthesis.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .debate_protocol import (
    BoardSynthesisContent,
    ElectionContent,
    publish_board_synthesis,
    publish_election,
)
from .hr_agents import HRAgent
from .hr_agents.culture_fit_agent import CultureFitAgent
from .hr_agents.growth_potential_agent import GrowthPotentialAgent
from .hr_agents.market_competitiveness_agent import MarketCompAgent
from .hr_agents.retention_risk_agent import RetentionRiskAgent
from .hr_agents.team_dynamics_agent import TeamDynamicsAgent
from .hr_agents.technical_depth_agent import TechnicalDepthAgent
from .message_bus import Message, MessageBus
from .orchestrator import AgentRole, DebateDepth, MiroFishSignal, Orchestrator

logger = logging.getLogger(__name__)


@dataclass
class SwarmConsensus:
    """Result of a swarm's internal debate."""

    swarm_id: str
    elected_agent_id: str
    elected_specialty: str
    recommendation: str
    confidence: float
    proposal_summary: str
    dissenting_views: List[str]
    debate_rounds: int


class SubSwarm:
    """A swarm of 2 agents debating in a domain."""

    def __init__(
        self,
        swarm_id: str,
        agents: List[HRAgent],
        message_bus: MessageBus,
    ):
        """
        Initialize a sub-swarm.

        Args:
            swarm_id: ID of this swarm (e.g., "culture_swarm")
            agents: List of HRAgent instances in this swarm (typically 2)
            message_bus: Shared message bus
        """
        self.swarm_id = swarm_id
        self.agents = agents
        self.message_bus = message_bus
        self.logger = logging.getLogger(f"{__name__}.{swarm_id}")

    async def internal_debate(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
        depth: DebateDepth,
    ) -> SwarmConsensus:
        """
        Run internal debate within this swarm.

        Flow depends on DebateDepth:
        - MINIMAL: skip debate, first agent's proposal wins
        - LIGHT: propose only, no challenge/reconcile
        - FULL: propose → challenge → reconcile

        Args:
            candidate_data: Candidate information
            mirofish_signal: MiroFish oracle signal
            depth: Debate depth (MINIMAL/LIGHT/FULL)

        Returns:
            SwarmConsensus with elected representative
        """
        if depth == DebateDepth.MINIMAL:
            return await self._run_minimal(candidate_data, mirofish_signal)
        elif depth == DebateDepth.LIGHT:
            return await self._run_light(candidate_data, mirofish_signal)
        else:  # FULL
            return await self._run_full(candidate_data, mirofish_signal)

    async def _run_minimal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> SwarmConsensus:
        """Skip debate, use first agent's proposal."""
        agent = self.agents[0]
        msg_id = await agent.propose(candidate_data, mirofish_signal)
        proposal_msg = self._get_message_by_id(msg_id)

        self.logger.info(
            f"[MINIMAL] {self.swarm_id}: {agent.agent_id} proposal stands"
        )

        # Publish election
        election_content: ElectionContent = {
            "swarm_id": self.swarm_id,
            "elected_agent_id": agent.agent_id,
            "elected_specialty": agent.specialty,
            "election_reason": "Minimal debate - signal is clear",
            "winning_confidence": proposal_msg.content["confidence"],
            "proposal_summary": proposal_msg.content["summary"],
            "dissenting_views": [],
        }
        await publish_election(
            self.message_bus,
            self.swarm_id,
            agent.agent_id,
            agent.specialty,
            election_content,
        )

        return SwarmConsensus(
            swarm_id=self.swarm_id,
            elected_agent_id=agent.agent_id,
            elected_specialty=agent.specialty,
            recommendation=proposal_msg.content["recommendation"],
            confidence=proposal_msg.content["confidence"],
            proposal_summary=proposal_msg.content["summary"],
            dissenting_views=[],
            debate_rounds=0,
        )

    async def _run_light(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> SwarmConsensus:
        """Light debate: each agent proposes, highest wins."""
        proposals: Dict[str, Message] = {}

        # Gather proposals from all agents
        for agent in self.agents:
            msg_id = await agent.propose(candidate_data, mirofish_signal)
            msg = self._get_message_by_id(msg_id)
            proposals[agent.agent_id] = msg

        # Elect by highest confidence
        elected_id = max(
            proposals.keys(),
            key=lambda a_id: proposals[a_id].content["confidence"],
        )
        elected_proposal = proposals[elected_id]
        elected_agent = next(a for a in self.agents if a.agent_id == elected_id)

        dissenting = [
            f"{a.agent_id}: {proposals[a.agent_id].content['recommendation']}"
            for a in self.agents
            if a.agent_id != elected_id
        ]

        self.logger.info(
            f"[LIGHT] {self.swarm_id}: elected {elected_agent.agent_id} "
            f"({elected_proposal.content['recommendation']}, "
            f"{elected_proposal.content['confidence']:.0%})"
        )

        # Publish election
        election_content: ElectionContent = {
            "swarm_id": self.swarm_id,
            "elected_agent_id": elected_agent.agent_id,
            "elected_specialty": elected_agent.specialty,
            "election_reason": "Highest confidence in light debate",
            "winning_confidence": elected_proposal.content["confidence"],
            "proposal_summary": elected_proposal.content["summary"],
            "dissenting_views": dissenting,
        }
        await publish_election(
            self.message_bus,
            self.swarm_id,
            elected_agent.agent_id,
            elected_agent.specialty,
            election_content,
        )

        return SwarmConsensus(
            swarm_id=self.swarm_id,
            elected_agent_id=elected_agent.agent_id,
            elected_specialty=elected_agent.specialty,
            recommendation=elected_proposal.content["recommendation"],
            confidence=elected_proposal.content["confidence"],
            proposal_summary=elected_proposal.content["summary"],
            dissenting_views=dissenting,
            debate_rounds=1,
        )

    async def _run_full(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> SwarmConsensus:
        """Full debate: propose → challenge → reconcile."""
        if len(self.agents) < 2:
            # Single agent, skip debate
            agent = self.agents[0]
            msg_id = await agent.propose(candidate_data, mirofish_signal)
            msg = self._get_message_by_id(msg_id)
            return SwarmConsensus(
                swarm_id=self.swarm_id,
                elected_agent_id=agent.agent_id,
                elected_specialty=agent.specialty,
                recommendation=msg.content["recommendation"],
                confidence=msg.content["confidence"],
                proposal_summary=msg.content["summary"],
                dissenting_views=[],
                debate_rounds=0,
            )

        # Round 1: Proposals
        proposals: Dict[str, Message] = {}
        for agent in self.agents:
            msg_id = await agent.propose(candidate_data, mirofish_signal)
            msg = self._get_message_by_id(msg_id)
            proposals[agent.agent_id] = msg

        # Round 2: Challenge
        proposer = self.agents[0]
        challenger = self.agents[1]
        proposal_msg = proposals[proposer.agent_id]

        challenge_msg_id = await challenger.challenge_proposal(
            proposal_msg, candidate_data
        )
        challenge_msg = self._get_message_by_id(challenge_msg_id)

        # Round 3: Reconcile
        reconcile_msg_id = await proposer.reconcile_challenge(
            challenge_msg, proposal_msg, candidate_data
        )
        reconcile_msg = self._get_message_by_id(reconcile_msg_id)

        # Elect highest confidence after debate
        final_confidence = reconcile_msg.content["updated_confidence"]
        challenger_confidence = proposals[challenger.agent_id].content["confidence"]

        elected_agent = (
            proposer
            if final_confidence >= challenger_confidence
            else challenger
        )

        self.logger.info(
            f"[FULL] {self.swarm_id}: elected {elected_agent.agent_id} "
            f"({reconcile_msg.content['updated_recommendation']}, "
            f"{final_confidence:.0%})"
        )

        # Publish election
        election_content: ElectionContent = {
            "swarm_id": self.swarm_id,
            "elected_agent_id": elected_agent.agent_id,
            "elected_specialty": elected_agent.specialty,
            "election_reason": "Highest confidence after full debate (propose/challenge/reconcile)",
            "winning_confidence": final_confidence,
            "proposal_summary": reconcile_msg.content["updated_summary"],
            "dissenting_views": [
                f"{challenger.agent_id}: {proposals[challenger.agent_id].content['recommendation']}"
            ],
        }
        await publish_election(
            self.message_bus,
            self.swarm_id,
            elected_agent.agent_id,
            elected_agent.specialty,
            election_content,
        )

        return SwarmConsensus(
            swarm_id=self.swarm_id,
            elected_agent_id=elected_agent.agent_id,
            elected_specialty=elected_agent.specialty,
            recommendation=reconcile_msg.content["updated_recommendation"],
            confidence=final_confidence,
            proposal_summary=reconcile_msg.content["updated_summary"],
            dissenting_views=[
                f"{challenger.agent_id}: {proposals[challenger.agent_id].content['recommendation']}"
            ],
            debate_rounds=3,
        )

    def _get_message_by_id(self, message_id: str) -> Message:
        """Get a message from transcript by ID (linear search, OK for small transcripts)."""
        transcript = self.message_bus.get_transcript()
        for msg in transcript:
            if msg.message_id == message_id:
                return msg
        raise ValueError(f"Message {message_id} not found in transcript")


class AgentBoard:
    """Orchestrates 3 swarms and synthesizes board decision."""

    def __init__(self, orchestrator: Orchestrator):
        """
        Initialize the agent board.

        Args:
            orchestrator: The Orchestrator instance (provides agents, signals, bus)
        """
        self.orchestrator = orchestrator
        self.message_bus = orchestrator.message_bus
        self.logger = logging.getLogger(__name__)
        self._confidence_trajectory: List[Dict[str, Any]] = []

    async def run_full_debate(
        self,
        candidate_data: Dict[str, Any],
    ) -> BoardSynthesisContent:
        """
        Run complete debate: swarm debates → elect reps → board synthesis.

        Args:
            candidate_data: Candidate information dict

        Returns:
            BoardSynthesisContent with final recommendation
        """
        # Phase 1: Get signals
        mirofish_signal = self.orchestrator.get_mirofish_signal()
        debate_depth = self.orchestrator.get_debate_depth()

        if not mirofish_signal or not debate_depth:
            raise ValueError(
                "Orchestrator must call read_mirofish() and assess_signal() first"
            )

        # Phase 2: Record initial confidence
        self._confidence_trajectory.append(
            {
                "phase": "mirofish_initial",
                "confidence": mirofish_signal.confidence,
            }
        )

        # Phase 3: Run swarm debates in parallel
        swarm_results = await self._run_swarm_debates(
            candidate_data, mirofish_signal, debate_depth
        )

        # Phase 4: Record swarm confidence
        avg_swarm_confidence = sum(
            r.confidence for r in swarm_results.values()
        ) / len(swarm_results)
        self._confidence_trajectory.append(
            {
                "phase": "swarm_debate",
                "confidence": avg_swarm_confidence,
            }
        )

        # Phase 5: Board synthesis
        board_content = await self._board_synthesis(
            swarm_results, mirofish_signal
        )

        # Phase 6: Record final confidence
        self._confidence_trajectory.append(
            {
                "phase": "board_synthesis",
                "confidence": board_content["final_confidence"],
            }
        )
        self._confidence_trajectory.append(
            {
                "phase": "orchestrator_final",
                "confidence": board_content["final_confidence"],
            }
        )

        # Phase 7: Publish board synthesis
        board_id = self.orchestrator.orchestrator_id
        await publish_board_synthesis(self.message_bus, board_id, board_content)

        return board_content

    async def _run_swarm_debates(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
        depth: DebateDepth,
    ) -> Dict[str, SwarmConsensus]:
        """Run all 3 swarms in parallel."""
        swarms = self._create_swarms()

        # Run all 3 in parallel
        results = await asyncio.gather(
            swarms["culture_swarm"].internal_debate(
                candidate_data, mirofish_signal, depth
            ),
            swarms["skill_swarm"].internal_debate(
                candidate_data, mirofish_signal, depth
            ),
            swarms["retention_swarm"].internal_debate(
                candidate_data, mirofish_signal, depth
            ),
        )

        # Map back to swarm IDs
        return {
            "culture_swarm": results[0],
            "skill_swarm": results[1],
            "retention_swarm": results[2],
        }

    async def _board_synthesis(
        self,
        swarm_results: Dict[str, SwarmConsensus],
        mirofish_signal: MiroFishSignal,
    ) -> BoardSynthesisContent:
        """Synthesize 3 swarm inputs into final recommendation (rule-based, no LLM)."""
        # Count recommendations
        rec_counts: Dict[str, int] = {}
        confidence_sum = 0.0

        for swarm_id, result in swarm_results.items():
            rec = result.recommendation
            rec_counts[rec] = rec_counts.get(rec, 0) + 1
            confidence_sum += result.confidence

        avg_confidence = confidence_sum / len(swarm_results)

        # Majority vote
        majority_rec = max(
            rec_counts.keys(), key=lambda r: rec_counts[r]
        )

        # Detect tensions
        tensions: List[str] = []
        unique_recs = len(rec_counts)
        if unique_recs > 1:
            tensions.append(f"Swarms disagree: {', '.join(sorted(rec_counts.keys()))}")

        # Confidence adjustment based on disagreement
        if unique_recs > 1:
            # Lower confidence if swarms disagree
            avg_confidence = max(0.3, avg_confidence - 0.05)

        # Ensure recommendation is valid
        valid_recs = ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]
        if majority_rec not in valid_recs:
            majority_rec = "HOLD"

        # Build swarm inputs summary
        swarm_inputs = {
            swarm_id: result.recommendation
            for swarm_id, result in swarm_results.items()
        }

        rationale = (
            f"Board recommendation: {majority_rec} ({avg_confidence:.0%} confidence). "
        )
        if unique_recs > 1:
            rationale += (
                f"Swarms provided mixed signals but aligned on: {majority_rec}. "
            )
        rationale += "See full debate transcript for detailed reasoning."

        content: BoardSynthesisContent = {
            "final_recommendation": majority_rec,
            "final_confidence": avg_confidence,
            "board_rationale": rationale,
            "cross_domain_tensions": tensions,
            "swarm_inputs": swarm_inputs,
            "confidence_trajectory": self._confidence_trajectory,
            "escalation_count": 0,  # TODO: track escalations
        }

        self.logger.info(
            f"[BOARD] final: {majority_rec} ({avg_confidence:.0%})"
        )

        return content

    def _create_swarms(self) -> Dict[str, SubSwarm]:
        """Create SubSwarm instances from orchestrator's agents."""
        swarms_dict = self.orchestrator.get_swarms()

        swarm_agents: Dict[str, List[HRAgent]] = {
            "culture_swarm": [],
            "skill_swarm": [],
            "retention_swarm": [],
        }

        # Map agent roles to agent instances
        for swarm_id in swarm_agents.keys():
            roles = swarms_dict.get(swarm_id, [])
            for role in roles:
                agent = self._instantiate_agent(role)
                swarm_agents[swarm_id].append(agent)

        # Create SubSwarm objects
        return {
            swarm_id: SubSwarm(swarm_id, agents, self.message_bus)
            for swarm_id, agents in swarm_agents.items()
        }

    def _instantiate_agent(self, role: AgentRole) -> HRAgent:
        """Create an HRAgent instance from an AgentRole."""
        agent_id = role.agent_id
        specialty = role.specialty

        if specialty == "culture_fit":
            return CultureFitAgent(role, self.message_bus)
        elif specialty == "team_dynamics":
            return TeamDynamicsAgent(role, self.message_bus)
        elif specialty == "technical_depth":
            return TechnicalDepthAgent(role, self.message_bus)
        elif specialty == "growth_potential":
            return GrowthPotentialAgent(role, self.message_bus)
        elif specialty == "retention_risk":
            return RetentionRiskAgent(role, self.message_bus)
        elif specialty == "market_competitiveness":
            return MarketCompAgent(role, self.message_bus)
        else:
            raise ValueError(f"Unknown specialty: {specialty}")

    def get_confidence_trajectory(self) -> List[Dict[str, Any]]:
        """Get confidence trajectory across debate phases."""
        return self._confidence_trajectory

    def get_full_transcript(self) -> List[Message]:
        """Get full debate transcript from message bus."""
        return self.message_bus.get_transcript()
