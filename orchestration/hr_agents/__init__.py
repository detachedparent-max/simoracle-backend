"""
HR Agent Base Class

All 6 domain agents extend HRAgent.
Provides stub-by-default pattern with LLM interface hook.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..message_bus import Message, MessageBus, MessageType
from ..orchestrator import AgentRole, MiroFishSignal

logger = logging.getLogger(__name__)

# Global LLM flag (can be overridden via USE_LLM env var)
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"


class HRAgent(ABC):
    """Base class for all HR domain agents."""

    def __init__(self, role: AgentRole, message_bus: MessageBus):
        """
        Initialize an HR agent.

        Args:
            role: AgentRole defining agent_id, specialty, swarm_id, etc.
            message_bus: Shared MessageBus instance for message routing
        """
        self.role = role
        self.message_bus = message_bus
        self.logger = logging.getLogger(f"{__name__}.{role.agent_id}")

    # ─── Properties ──────────────────────────────────────────────────────
    @property
    def agent_id(self) -> str:
        """Agent identifier."""
        return self.role.agent_id

    @property
    def specialty(self) -> str:
        """Agent's domain specialty."""
        return self.role.specialty

    @property
    def swarm_id(self) -> str:
        """Swarm ID this agent belongs to."""
        return self.role.swarm_id

    # ─── Abstract Methods (subclasses must override) ──────────────────────
    @abstractmethod
    async def generate_proposal(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
    ) -> Dict[str, Any]:
        """
        Generate initial proposal based on candidate data.

        Must return a ProposalContent dict with:
        - specialty, swarm_id, recommendation, confidence, summary
        - key_factors, risk_flags, mirofish_alignment, raw_score

        Args:
            candidate_data: Candidate info dict
            mirofish_signal: MiroFish oracle signal

        Returns:
            ProposalContent dict
        """
        pass

    @abstractmethod
    async def generate_challenge(
        self,
        proposal: Message,
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate challenge to a proposal from another agent.

        Must return a ChallengeContent dict with:
        - challenger_specialty, challenge_type, challenge_text
        - counter_evidence, confidence_impact

        Args:
            proposal: The Message object being challenged
            candidate_data: Candidate info dict

        Returns:
            ChallengeContent dict
        """
        pass

    @abstractmethod
    async def generate_reconciliation(
        self,
        challenge: Message,
        original_proposal: Message,
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Respond to a challenge (defend, accept, or partially accept).

        Must return a ReconciliationContent dict with:
        - resolution, updated_recommendation, updated_confidence
        - updated_summary, response_to_challenge, new_evidence, escalated

        Args:
            challenge: The challenge Message being responded to
            original_proposal: The original proposal Message
            candidate_data: Candidate info dict

        Returns:
            ReconciliationContent dict
        """
        pass

    # ─── LLM Interface (override in subclass to enable real LLM) ──────────
    async def call_llm(self, prompt: str) -> str:
        """
        Call Claude API for reasoning (stub by default).

        Override in subclass to enable real LLM calls.

        Args:
            prompt: The prompt to send to Claude

        Returns:
            LLM response text

        Raises:
            NotImplementedError: If USE_LLM=true but not overridden
        """
        if USE_LLM:
            raise NotImplementedError(
                f"{self.agent_id} does not implement call_llm(). "
                "Override this method in subclass or set USE_LLM=false."
            )
        # Stub mode: return empty string (subclass should not call this)
        return ""

    # ─── Protocol Helpers (use debate_protocol functions internally) ──────
    async def propose(
        self,
        candidate_data: Dict[str, Any],
        mirofish_signal: MiroFishSignal,
        receivers: Optional[list[str]] = None,
    ) -> str:
        """
        Send a proposal to the message bus.

        Args:
            candidate_data: Candidate info
            mirofish_signal: MiroFish signal
            receivers: Optional receiver agent IDs

        Returns:
            message_id of sent proposal
        """
        from ..debate_protocol import propose as protocol_propose

        content = await self.generate_proposal(candidate_data, mirofish_signal)
        return await protocol_propose(
            self.message_bus, self.role, content, receivers
        )

    async def challenge_proposal(
        self,
        proposal_msg: Message,
        candidate_data: Dict[str, Any],
        receivers: Optional[list[str]] = None,
    ) -> str:
        """
        Send a challenge to a proposal.

        Args:
            proposal_msg: The proposal Message to challenge
            candidate_data: Candidate info
            receivers: Optional receiver agent IDs

        Returns:
            message_id of sent challenge
        """
        from ..debate_protocol import challenge as protocol_challenge

        content = await self.generate_challenge(proposal_msg.content, candidate_data)
        return await protocol_challenge(
            self.message_bus,
            self.role,
            proposal_msg.message_id,
            content,
            receivers,
        )

    async def reconcile_challenge(
        self,
        challenge_msg: Message,
        original_proposal_msg: Message,
        candidate_data: Dict[str, Any],
        receivers: Optional[list[str]] = None,
    ) -> str:
        """
        Respond to a challenge (reconciliation).

        Args:
            challenge_msg: The challenge Message
            original_proposal_msg: The original proposal being challenged
            candidate_data: Candidate info
            receivers: Optional receiver agent IDs

        Returns:
            message_id of sent reconciliation
        """
        from ..debate_protocol import reconcile as protocol_reconcile

        content = await self.generate_reconciliation(
            challenge_msg.content, original_proposal_msg.content, candidate_data
        )
        return await protocol_reconcile(
            self.message_bus,
            self.role,
            challenge_msg.message_id,
            content,
            receivers,
        )

    async def maybe_escalate(
        self,
        reason: str,
        confidence: float,
        parent_msg_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Request escalation to MiroFish if confidence is too low.

        Args:
            reason: Reason for escalation
            confidence: Current confidence level
            parent_msg_id: Parent message ID for threading

        Returns:
            message_id of escalation message, or None if not escalated
        """
        # Stub: agents can call this but it's optional
        # Actual escalation logic depends on debate_depth + confidence
        if confidence < 0.5:
            from ..debate_protocol import escalate_to_mirofish

            return await escalate_to_mirofish(
                self.message_bus,
                self.role,
                f"Low confidence proposal: {reason}",
                reason,
                confidence,
                parent_msg_id,
            )
        return None

    # ─── Utilities ─────────────────────────────────────────────────────
    def score_recommendation(self, confidence: float) -> str:
        """Map confidence to recommendation category."""
        if confidence >= 0.85:
            return "STRONG_HIRE"
        elif confidence >= 0.70:
            return "HIRE"
        elif confidence >= 0.50:
            return "HOLD"
        elif confidence >= 0.35:
            return "PASS"
        else:
            return "STRONG_PASS"

    def _log_proposal(self, recommendation: str, confidence: float):
        """Log proposal for debugging."""
        self.logger.debug(
            f"[{self.specialty}] proposal: {recommendation} (conf: {confidence:.0%})"
        )

    def _log_challenge(self, challenge_type: str):
        """Log challenge for debugging."""
        self.logger.debug(f"[{self.specialty}] challenge: {challenge_type}")

    def _log_reconciliation(self, resolution: str, confidence: float):
        """Log reconciliation for debugging."""
        self.logger.debug(
            f"[{self.specialty}] reconciliation: {resolution} (conf: {confidence:.0%})"
        )
