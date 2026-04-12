"""
Debate Protocol Functions

Stateless async functions for the propose → challenge → reconcile → escalate flow.
All functions create Message objects and send them via MessageBus.
No state lives here — it all lives in MessageBus.transcript.

Content shape contracts are defined as TypedDicts so downstream code has clear expectations.
"""

import logging
from typing import Any, Dict, Optional, TypedDict
from uuid import uuid4

from .message_bus import Message, MessageBus, MessageType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE CONTENT TYPE DEFINITIONS
# These TypedDicts define the exact shape of message.content for each type.
# ─────────────────────────────────────────────────────────────────────────────


class ProposalContent(TypedDict):
    """Content of a PROPOSAL message."""

    specialty: str  # e.g. "culture_fit"
    swarm_id: str  # e.g. "culture_swarm"
    recommendation: str  # "STRONG_HIRE" | "HIRE" | "HOLD" | "PASS" | "STRONG_PASS"
    confidence: float  # 0.0–1.0
    summary: str  # 1-2 sentence plain-English finding
    key_factors: list[str]  # 2-4 bullet factors supporting recommendation
    risk_flags: list[str]  # 0-3 risks identified
    mirofish_alignment: str  # "supports" | "contradicts" | "extends"
    raw_score: float  # 0.0–1.0 domain-specific score


class ChallengeContent(TypedDict):
    """Content of a CHALLENGE message."""

    challenger_specialty: str  # specialty of challenging agent
    challenge_type: str  # "assumption" | "missing_data" | "counter_evidence" | "scope"
    challenge_text: str  # The actual challenge argument
    counter_evidence: list[str]  # Evidence points backing the challenge
    confidence_impact: float  # Estimated confidence delta (-0.3 to 0.0)


class ReconciliationContent(TypedDict):
    """Content of a RECONCILIATION message."""

    resolution: str  # "accepted" | "partial" | "defended"
    updated_recommendation: str  # May be same or revised
    updated_confidence: float  # Revised confidence after challenge
    updated_summary: str  # Revised summary
    response_to_challenge: str  # Direct response to the challenge argument
    new_evidence: list[str]  # Any new supporting evidence
    escalated: bool  # Whether this triggered MiroFish escalation


class EscalationContent(TypedDict):
    """Content of an ESCALATION message."""

    escalating_agent: str
    escalating_specialty: str
    scenario: str  # The specific scenario to simulate
    reason: str  # Why escalation was needed
    original_confidence: float  # Confidence before escalation


class EscalationResultContent(TypedDict):
    """Content of an ESCALATION_RESULT message."""

    scenario: str
    new_probability: float
    new_confidence: float
    confidence_delta: float  # vs. original MiroFish signal
    narrative: str
    agent_id: str


class ElectionContent(TypedDict):
    """Content of an ELECTION message."""

    swarm_id: str
    elected_agent_id: str
    elected_specialty: str
    election_reason: str  # "highest_confidence" | "strongest_evidence" | "consensus"
    winning_confidence: float
    proposal_summary: str  # The winning proposal's summary (for board)
    dissenting_views: list[str]  # Minority opinions from other swarm members


class BoardSynthesisContent(TypedDict):
    """Content of a BOARD_SYNTHESIS message."""

    final_recommendation: str  # "STRONG_HIRE" | "HIRE" | "HOLD" | "PASS" | "STRONG_PASS"
    final_confidence: float
    board_rationale: str
    cross_domain_tensions: list[str]  # Trade-offs the board weighed
    swarm_inputs: dict[str, str]  # swarm_id → their recommendation
    confidence_trajectory: list[dict]  # [{"phase": str, "confidence": float}, ...]
    escalation_count: int


# ─────────────────────────────────────────────────────────────────────────────
# PROTOCOL FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────


async def propose(
    message_bus: MessageBus,
    agent_role: Any,  # AgentRole — typed loosely to avoid circular import
    content: ProposalContent,
    receivers: Optional[list[str]] = None,
) -> str:
    """
    Agent sends initial proposal to message bus.

    Args:
        message_bus: The active MessageBus instance
        agent_role: The AgentRole of the proposing agent
        content: ProposalContent dict
        receivers: Optional list of receiver IDs. Defaults to None (broadcast to all).

    Returns:
        message_id of the sent proposal
    """
    msg = Message(
        sender_id=agent_role.agent_id,
        message_type=MessageType.PROPOSAL,
        content=content,
    )
    msg_id = await message_bus.send(msg, receivers)
    logger.debug(
        f"[PROPOSE] {agent_role.agent_id} → {content['recommendation']} ({content['confidence']:.0%})"
    )
    return msg_id


async def challenge(
    message_bus: MessageBus,
    challenger_role: Any,
    parent_message_id: str,
    content: ChallengeContent,
    receivers: Optional[list[str]] = None,
) -> str:
    """
    Agent challenges an existing proposal.

    parent_message_id threads this challenge to the proposal.

    Args:
        message_bus: The active MessageBus instance
        challenger_role: The AgentRole of the challenging agent
        parent_message_id: ID of the proposal being challenged
        content: ChallengeContent dict
        receivers: Optional receiver IDs

    Returns:
        message_id of the sent challenge
    """
    msg = Message(
        sender_id=challenger_role.agent_id,
        message_type=MessageType.CHALLENGE,
        content=content,
        parent_message_id=parent_message_id,
    )
    msg_id = await message_bus.send(msg, receivers)
    logger.debug(
        f"[CHALLENGE] {challenger_role.agent_id} challenged {parent_message_id[:8]}: {content['challenge_type']}"
    )
    return msg_id


async def reconcile(
    message_bus: MessageBus,
    proposer_role: Any,
    parent_message_id: str,  # ID of the challenge message
    content: ReconciliationContent,
    receivers: Optional[list[str]] = None,
) -> str:
    """
    Proposer responds to a challenge (accept, defend, or partially accept).

    parent_message_id threads this to the challenge.

    Args:
        message_bus: The active MessageBus instance
        proposer_role: The AgentRole of the proposing agent
        parent_message_id: ID of the challenge being responded to
        content: ReconciliationContent dict
        receivers: Optional receiver IDs

    Returns:
        message_id of the sent reconciliation
    """
    msg = Message(
        sender_id=proposer_role.agent_id,
        message_type=MessageType.RECONCILIATION,
        content=content,
        parent_message_id=parent_message_id,
    )
    msg_id = await message_bus.send(msg, receivers)
    logger.debug(
        f"[RECONCILE] {proposer_role.agent_id} → {content['resolution']} (conf: {content['updated_confidence']:.0%})"
    )
    return msg_id


async def escalate_to_mirofish(
    message_bus: MessageBus,
    agent_role: Any,
    scenario: str,
    reason: str,
    original_confidence: float,
    parent_message_id: Optional[str] = None,
) -> str:
    """
    Agent requests additional MiroFish simulation mid-debate.

    Sends ESCALATION message to transcript. The actual simulation result
    must be published separately via publish_escalation_result().

    Args:
        message_bus: The active MessageBus instance
        agent_role: The AgentRole of the escalating agent
        scenario: Description of scenario to simulate
        reason: Reason for escalation
        original_confidence: Current confidence level
        parent_message_id: Optional parent message ID for threading

    Returns:
        message_id of the escalation message
    """
    content: EscalationContent = {
        "escalating_agent": agent_role.agent_id,
        "escalating_specialty": agent_role.specialty,
        "scenario": scenario,
        "reason": reason,
        "original_confidence": original_confidence,
    }
    msg = Message(
        sender_id=agent_role.agent_id,
        message_type=MessageType.ESCALATION,
        content=content,
        parent_message_id=parent_message_id,
    )
    msg_id = await message_bus.send(msg)
    logger.info(
        f"[ESCALATION] {agent_role.agent_id} escalated: {scenario[:60]}"
    )
    return msg_id


async def publish_escalation_result(
    message_bus: MessageBus,
    agent_role: Any,
    escalation_message_id: str,
    new_probability: float,
    new_confidence: float,
    original_confidence: float,
    scenario: str,
    narrative: str,
) -> str:
    """
    Publish the result of a MiroFish escalation back to the transcript.

    In production this would call the actual MiroFish API.
    For now, produces a result based on scenario keywords.

    Args:
        message_bus: The active MessageBus instance
        agent_role: The AgentRole of the agent requesting escalation
        escalation_message_id: ID of the escalation message
        new_probability: New probability from MiroFish
        new_confidence: New confidence from MiroFish
        original_confidence: Previous confidence level
        scenario: The scenario that was simulated
        narrative: Narrative explanation of result

    Returns:
        message_id of the escalation result message
    """
    content: EscalationResultContent = {
        "scenario": scenario,
        "new_probability": new_probability,
        "new_confidence": new_confidence,
        "confidence_delta": new_confidence - original_confidence,
        "narrative": narrative,
        "agent_id": agent_role.agent_id,
    }
    msg = Message(
        sender_id=agent_role.agent_id,
        message_type=MessageType.ESCALATION_RESULT,
        content=content,
        parent_message_id=escalation_message_id,
    )
    return await message_bus.send(msg)


async def publish_election(
    message_bus: MessageBus,
    swarm_id: str,
    elected_agent_id: str,
    elected_specialty: str,
    content: ElectionContent,
    receivers: Optional[list[str]] = None,
) -> str:
    """
    Swarm publishes its elected representative to the board.

    sender_id is the swarm_id (not an individual agent).

    Args:
        message_bus: The active MessageBus instance
        swarm_id: ID of the swarm publishing the election
        elected_agent_id: ID of the elected representative
        elected_specialty: Specialty of the elected agent
        content: ElectionContent dict
        receivers: Optional receiver IDs

    Returns:
        message_id of the election message
    """
    msg = Message(
        sender_id=swarm_id,
        message_type=MessageType.ELECTION,
        content=content,
    )
    return await message_bus.send(msg, receivers)


async def publish_board_synthesis(
    message_bus: MessageBus,
    board_id: str,
    content: BoardSynthesisContent,
) -> str:
    """
    Board publishes final synthesis and recommendation.

    This is the final message in the debate flow.

    Args:
        message_bus: The active MessageBus instance
        board_id: ID of the board (e.g., "board" or "orchestrator_{domain}")
        content: BoardSynthesisContent dict

    Returns:
        message_id of the board synthesis message
    """
    msg = Message(
        sender_id=board_id,
        message_type=MessageType.BOARD_SYNTHESIS,
        content=content,
    )
    msg_id = await message_bus.send(msg)
    logger.info(
        f"[BOARD_SYNTHESIS] final recommendation: {content['final_recommendation']} "
        f"(conf: {content['final_confidence']:.0%})"
    )
    return msg_id
