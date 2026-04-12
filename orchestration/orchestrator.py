"""
Lead Orchestrator — Chief Decision Officer

Entry point for the agent orchestration system.
- Spawns agents
- Reads MiroFish signals
- Decides debate depth
- Delegates to board
- Synthesizes final decision
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .message_bus import MessageBus, Message, MessageType

logger = logging.getLogger(__name__)


class DebateDepth(Enum):
    """How deep should the debate go?"""
    MINIMAL = "minimal"      # Signal is clear, skip debate
    LIGHT = "light"          # Some uncertainty, quick due diligence
    FULL = "full"            # High uncertainty, comprehensive debate


@dataclass
class MiroFishSignal:
    """Signal from MiroFish simulations"""
    probability: float           # 0-1, the core prediction
    confidence: float            # 0-1, how sure are we?
    agent_diversity: float       # 0-1, do agents agree?
    convergence_rounds: int      # How many rounds to stabilize?
    variance: float              # Spread of agent outputs
    drift: float                 # Movement across rounds
    narrative: Optional[str] = None  # Optional explanation


@dataclass
class AgentRole:
    """Definition of an agent's role"""
    agent_id: str                # Unique identifier
    domain: str                  # "hr", "mna", "real_estate"
    specialty: str               # "culture_fit", "skill_depth", etc.
    swarm_id: str               # "culture_swarm", "skill_swarm", etc.
    api_key: Optional[str] = None  # Customer's API key (shared context)
    instructions: str = ""       # System prompt for agent


class Orchestrator:
    """
    Lead Orchestrator (Chief Decision Officer)

    Controls the entire agent orchestration flow:
    1. Spawns agents based on domain
    2. Reads MiroFish signal
    3. Assesses debate depth
    4. Delegates to board for debate
    5. Coordinates synthesis
    6. Produces final decision
    """

    def __init__(self, domain: str, shared_api_key: Optional[str] = None):
        """
        Initialize orchestrator.

        Args:
            domain: Domain type ("hr", "mna", "real_estate")
            shared_api_key: Customer's API key (shared with all agents)
        """
        self.domain = domain
        self.shared_api_key = shared_api_key
        self.orchestrator_id = f"orchestrator_{domain}_{str(uuid4())[:8]}"

        # Agent registry
        self.agents: Dict[str, AgentRole] = {}
        self.swarms: Dict[str, List[AgentRole]] = {}

        # Message bus
        self.message_bus = MessageBus()

        # State
        self.mirofish_signal: Optional[MiroFishSignal] = None
        self.debate_depth: Optional[DebateDepth] = None
        self.started_at: datetime = datetime.now()

        logger.info(
            f"Orchestrator initialized: {self.orchestrator_id} "
            f"(domain: {domain})"
        )

    async def spawn_agents(self, swarm_config: Dict[str, List[Dict[str, str]]]):
        """
        Initialize agents based on domain and swarm configuration.

        Args:
            swarm_config: Dict mapping swarm_id to list of agent configs
                Example:
                {
                    "culture_swarm": [
                        {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
                        {"agent_id": "team_dynamics_agent", "specialty": "team_dynamics"},
                    ],
                    "skill_swarm": [...],
                    ...
                }
        """
        logger.info(f"Spawning agents for domain: {self.domain}")

        for swarm_id, agent_configs in swarm_config.items():
            self.swarms[swarm_id] = []

            for agent_config in agent_configs:
                agent_id = agent_config.get("agent_id")
                specialty = agent_config.get("specialty", agent_id)

                role = AgentRole(
                    agent_id=agent_id,
                    domain=self.domain,
                    specialty=specialty,
                    swarm_id=swarm_id,
                    api_key=self.shared_api_key,
                    instructions=agent_config.get("instructions", ""),
                )

                self.agents[agent_id] = role
                self.swarms[swarm_id].append(role)

                logger.debug(
                    f"Spawned agent: {agent_id} "
                    f"(specialty: {specialty}, swarm: {swarm_id})"
                )

        logger.info(
            f"Agents spawned: {len(self.agents)} total, "
            f"{len(self.swarms)} swarms"
        )

    async def read_mirofish(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> MiroFishSignal:
        """
        Read MiroFish signal from simulations.

        In production, this would call the actual MiroFish API.
        For now, it parses a mock signal.

        Args:
            question: Prediction question
            context: Domain context

        Returns:
            MiroFishSignal with probability, confidence, diversity, etc.
        """
        logger.info(f"Reading MiroFish signal for: {question[:50]}...")

        # TODO: In production, call actual MiroFish API
        # For now, return a realistic mock signal
        # In Week 1 testing, we'll use a test signal

        self.mirofish_signal = MiroFishSignal(
            probability=0.72,
            confidence=0.68,
            agent_diversity=0.15,
            convergence_rounds=12,
            variance=0.08,
            drift=0.02,
            narrative="Moderate signal, some agent disagreement",
        )

        logger.info(
            f"MiroFish signal: probability={self.mirofish_signal.probability:.0%}, "
            f"confidence={self.mirofish_signal.confidence:.0%}, "
            f"debate_depth will be: {self._assess_debate_depth().value}"
        )

        return self.mirofish_signal

    def _assess_debate_depth(self) -> DebateDepth:
        """
        Assess how deep the debate should go based on MiroFish signal.

        Logic:
        - confidence >= 0.85 AND diversity < 0.10 → minimal (signal is clear)
        - confidence >= 0.70 → light (some uncertainty)
        - else → full (high uncertainty)
        """
        if not self.mirofish_signal:
            return DebateDepth.FULL  # Default to full if no signal

        conf = self.mirofish_signal.confidence
        div = self.mirofish_signal.agent_diversity

        if conf >= 0.85 and div < 0.10:
            return DebateDepth.MINIMAL
        elif conf >= 0.70:
            return DebateDepth.LIGHT
        else:
            return DebateDepth.FULL

    async def assess_signal(self) -> DebateDepth:
        """
        Public method to assess signal and decide debate depth.

        Returns:
            DebateDepth (minimal, light, or full)
        """
        if not self.mirofish_signal:
            logger.warning("No MiroFish signal available, defaulting to FULL debate")
            return DebateDepth.FULL

        self.debate_depth = self._assess_debate_depth()
        logger.info(f"Debate depth: {self.debate_depth.value}")
        return self.debate_depth

    async def delegate_to_board(self, question: str, context: Dict[str, Any]):
        """
        Delegate to agent board for debate.

        Sends START_DEBATE message to all swarms.

        Args:
            question: Prediction question
            context: Domain context (candidate data, role data, etc.)
        """
        if not self.debate_depth:
            await self.assess_signal()

        logger.info(
            f"Delegating to board (depth: {self.debate_depth.value})"
        )

        # Send start_debate message to orchestrator (for board to receive)
        start_msg = Message(
            sender_id=self.orchestrator_id,
            message_type=MessageType.START_DEBATE,
            content={
                "question": question,
                "context": context,
                "mirofish_signal": {
                    "probability": self.mirofish_signal.probability,
                    "confidence": self.mirofish_signal.confidence,
                    "diversity": self.mirofish_signal.agent_diversity,
                    "convergence_rounds": self.mirofish_signal.convergence_rounds,
                    "variance": self.mirofish_signal.variance,
                    "drift": self.mirofish_signal.drift,
                },
                "debate_depth": self.debate_depth.value,
            },
        )

        # Broadcast to all swarms
        swarm_ids = list(self.swarms.keys())
        await self.message_bus.broadcast(start_msg, swarm_ids)

        logger.info(f"START_DEBATE sent to {len(swarm_ids)} swarms")

    def get_agents(self) -> Dict[str, AgentRole]:
        """Get all agents"""
        return self.agents.copy()

    def get_swarms(self) -> Dict[str, List[AgentRole]]:
        """Get all swarms"""
        return {k: v.copy() for k, v in self.swarms.items()}

    def get_agent(self, agent_id: str) -> Optional[AgentRole]:
        """Get a specific agent"""
        return self.agents.get(agent_id)

    def get_swarm(self, swarm_id: str) -> List[AgentRole]:
        """Get agents in a specific swarm"""
        return self.swarms.get(swarm_id, [])

    def get_mirofish_signal(self) -> Optional[MiroFishSignal]:
        """Get current MiroFish signal"""
        return self.mirofish_signal

    def get_debate_depth(self) -> Optional[DebateDepth]:
        """Get assessed debate depth"""
        return self.debate_depth

    def get_transcript(self) -> List[Message]:
        """Get full debate transcript"""
        return self.message_bus.get_transcript()

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "orchestrator_id": self.orchestrator_id,
            "domain": self.domain,
            "agent_count": len(self.agents),
            "swarm_count": len(self.swarms),
            "started_at": self.started_at.isoformat(),
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
            "message_bus_stats": self.message_bus.stats(),
            "mirofish_signal": {
                "probability": self.mirofish_signal.probability if self.mirofish_signal else None,
                "confidence": self.mirofish_signal.confidence if self.mirofish_signal else None,
                "diversity": self.mirofish_signal.agent_diversity if self.mirofish_signal else None,
            },
            "debate_depth": self.debate_depth.value if self.debate_depth else None,
        }
