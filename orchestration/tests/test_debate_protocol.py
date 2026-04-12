"""
Tests for debate_protocol functions.

Validates message creation, threading, TypedDict contracts, and transcript capture.
"""

import asyncio
import pytest
from typing import Dict, Any

from orchestration.message_bus import Message, MessageBus, MessageType
from orchestration.orchestrator import AgentRole, MiroFishSignal, DebateDepth
from orchestration.debate_protocol import (
    ProposalContent,
    ChallengeContent,
    ReconciliationContent,
    EscalationContent,
    EscalationResultContent,
    ElectionContent,
    BoardSynthesisContent,
    propose,
    challenge,
    reconcile,
    escalate_to_mirofish,
    publish_escalation_result,
    publish_election,
    publish_board_synthesis,
)


@pytest.fixture
def message_bus():
    """Create a fresh message bus for each test."""
    return MessageBus()


@pytest.fixture
def agent_role():
    """Create a test agent role."""
    return AgentRole(
        agent_id="test_agent_1",
        domain="hr",
        specialty="culture_fit",
        swarm_id="culture_swarm",
        instructions="Test instructions",
    )


@pytest.fixture
def challenger_role():
    """Create a challenger agent role."""
    return AgentRole(
        agent_id="test_agent_2",
        domain="hr",
        specialty="team_dynamics",
        swarm_id="culture_swarm",
        instructions="Test instructions",
    )


@pytest.fixture
def mirofish_signal():
    """Create a test MiroFish signal."""
    return MiroFishSignal(
        probability=0.75,
        confidence=0.85,
        agent_diversity=0.70,
        convergence_rounds=5,
        variance=0.10,
        drift=0.02,
        narrative="Test signal",
    )


@pytest.mark.asyncio
async def test_propose_sends_correct_message_type(message_bus, agent_role):
    """Test that propose() sends a PROPOSAL message."""
    content: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "HIRE",
        "confidence": 0.85,
        "summary": "Good culture fit",
        "key_factors": ["values alignment"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.85,
    }

    msg_id = await propose(message_bus, agent_role, content)

    assert msg_id is not None
    transcript = message_bus.get_transcript()
    assert len(transcript) == 1
    msg = transcript[0]
    assert msg.message_type == MessageType.PROPOSAL
    assert msg.sender_id == agent_role.agent_id
    assert msg.content == content


@pytest.mark.asyncio
async def test_propose_with_receivers(message_bus, agent_role, challenger_role):
    """Test that propose() accepts receivers parameter."""
    content: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "HIRE",
        "confidence": 0.85,
        "summary": "Good culture fit",
        "key_factors": ["values alignment"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.85,
    }

    msg_id = await propose(
        message_bus, agent_role, content, receivers=[challenger_role.agent_id]
    )

    transcript = message_bus.get_transcript()
    assert len(transcript) == 1
    msg = transcript[0]
    # Verify message was created and sent
    assert msg.sender_id == agent_role.agent_id
    assert msg.message_type == MessageType.PROPOSAL


@pytest.mark.asyncio
async def test_challenge_creates_parent_link(message_bus, agent_role, challenger_role):
    """Test that challenge() links to parent proposal via parent_message_id."""
    proposal_content: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "HIRE",
        "confidence": 0.85,
        "summary": "Good culture fit",
        "key_factors": ["values alignment"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.85,
    }

    proposal_id = await propose(message_bus, agent_role, proposal_content)

    challenge_content: ChallengeContent = {
        "challenger_specialty": "team_dynamics",
        "challenge_type": "assumption",
        "challenge_text": "Need to verify team chemistry",
        "counter_evidence": ["Different work styles"],
        "confidence_impact": -0.10,
    }

    challenge_id = await challenge(
        message_bus, challenger_role, proposal_id, challenge_content
    )

    transcript = message_bus.get_transcript()
    assert len(transcript) == 2
    challenge_msg = transcript[1]
    assert challenge_msg.message_type == MessageType.CHALLENGE
    assert challenge_msg.parent_message_id == proposal_id
    assert challenge_msg.content == challenge_content


@pytest.mark.asyncio
async def test_reconcile_creates_chain(message_bus, agent_role, challenger_role):
    """Test that reconcile() completes a propose→challenge→reconcile chain."""
    proposal_content: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "HIRE",
        "confidence": 0.85,
        "summary": "Good culture fit",
        "key_factors": ["values alignment"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.85,
    }

    proposal_id = await propose(message_bus, agent_role, proposal_content)

    challenge_content: ChallengeContent = {
        "challenger_specialty": "team_dynamics",
        "challenge_type": "assumption",
        "challenge_text": "Need to verify team chemistry",
        "counter_evidence": ["Different work styles"],
        "confidence_impact": -0.10,
    }

    challenge_id = await challenge(
        message_bus, challenger_role, proposal_id, challenge_content
    )

    reconcile_content: ReconciliationContent = {
        "resolution": "partial",
        "updated_recommendation": "HIRE",
        "updated_confidence": 0.80,
        "updated_summary": "Will assess team chemistry carefully",
        "response_to_challenge": "Fair point about team fit",
        "new_evidence": ["Team interviews scheduled"],
        "escalated": False,
    }

    reconcile_id = await reconcile(
        message_bus, agent_role, challenge_id, reconcile_content
    )

    transcript = message_bus.get_transcript()
    assert len(transcript) == 3
    reconcile_msg = transcript[2]
    assert reconcile_msg.message_type == MessageType.RECONCILIATION
    assert reconcile_msg.parent_message_id == challenge_id
    assert reconcile_msg.content == reconcile_content


@pytest.mark.asyncio
async def test_escalate_to_mirofish(message_bus, agent_role):
    """Test that escalate_to_mirofish() sends ESCALATION message."""
    escalation_content: EscalationContent = {
        "escalating_agent": agent_role.agent_id,
        "escalating_specialty": "culture_fit",
        "scenario": "Unclear hiring decision",
        "reason": "Conflicting signals from swarm debate",
        "original_confidence": 0.50,
    }

    escalation_id = await escalate_to_mirofish(
        message_bus,
        agent_role,
        escalation_content["scenario"],
        escalation_content["reason"],
        escalation_content["original_confidence"],
    )

    transcript = message_bus.get_transcript()
    assert len(transcript) == 1
    msg = transcript[0]
    assert msg.message_type == MessageType.ESCALATION
    assert msg.sender_id == agent_role.agent_id


@pytest.mark.asyncio
async def test_publish_escalation_result(message_bus, agent_role):
    """Test that publish_escalation_result() sends ESCALATION_RESULT message."""
    escalation_content: EscalationContent = {
        "escalating_agent": agent_role.agent_id,
        "escalating_specialty": "culture_fit",
        "scenario": "Unclear hiring decision",
        "reason": "Conflicting signals from swarm debate",
        "original_confidence": 0.50,
    }

    escalation_id = await escalate_to_mirofish(
        message_bus,
        agent_role,
        escalation_content["scenario"],
        escalation_content["reason"],
        escalation_content["original_confidence"],
    )

    result_id = await publish_escalation_result(
        message_bus,
        agent_role,
        escalation_id,
        0.65,
        0.72,
        0.50,
        "Unclear hiring decision",
        "MiroFish signal refines assessment",
    )

    transcript = message_bus.get_transcript()
    assert len(transcript) == 2
    result_msg = transcript[1]
    assert result_msg.message_type == MessageType.ESCALATION_RESULT
    assert result_msg.parent_message_id == escalation_id


@pytest.mark.asyncio
async def test_publish_election(message_bus):
    """Test that publish_election() sends ELECTION message."""
    election_content: ElectionContent = {
        "swarm_id": "culture_swarm",
        "elected_agent_id": "agent_1",
        "elected_specialty": "culture_fit",
        "election_reason": "Highest confidence after debate",
        "winning_confidence": 0.85,
        "proposal_summary": "Strong cultural fit",
        "dissenting_views": ["agent_2 recommended HOLD"],
    }

    msg_id = await publish_election(
        message_bus, "culture_swarm", "agent_1", "culture_fit", election_content
    )

    transcript = message_bus.get_transcript()
    assert len(transcript) == 1
    msg = transcript[0]
    assert msg.message_type == MessageType.ELECTION
    assert msg.content == election_content


@pytest.mark.asyncio
async def test_publish_board_synthesis(message_bus):
    """Test that publish_board_synthesis() sends BOARD_SYNTHESIS message."""
    board_content: BoardSynthesisContent = {
        "final_recommendation": "HIRE",
        "final_confidence": 0.82,
        "board_rationale": "Swarms aligned on strong hire candidate",
        "cross_domain_tensions": [],
        "swarm_inputs": {
            "culture_swarm": "HIRE",
            "skill_swarm": "STRONG_HIRE",
            "retention_swarm": "HIRE",
        },
        "confidence_trajectory": [
            {"phase": "mirofish_initial", "confidence": 0.75},
            {"phase": "swarm_debate", "confidence": 0.85},
            {"phase": "board_synthesis", "confidence": 0.82},
            {"phase": "orchestrator_final", "confidence": 0.82},
        ],
        "escalation_count": 0,
    }

    msg_id = await publish_board_synthesis(message_bus, "board_1", board_content)

    transcript = message_bus.get_transcript()
    assert len(transcript) == 1
    msg = transcript[0]
    assert msg.message_type == MessageType.BOARD_SYNTHESIS
    assert msg.content == board_content
    assert msg.sender_id == "board_1"


@pytest.mark.asyncio
async def test_multiple_proposals_in_transcript(message_bus, agent_role, challenger_role):
    """Test that multiple proposals from different agents are all captured."""
    content1: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "HIRE",
        "confidence": 0.85,
        "summary": "Good culture fit",
        "key_factors": ["values alignment"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.85,
    }

    content2: ProposalContent = {
        "specialty": "team_dynamics",
        "swarm_id": "culture_swarm",
        "recommendation": "HOLD",
        "confidence": 0.60,
        "summary": "Uncertain team dynamics",
        "key_factors": ["team_chemistry"],
        "risk_flags": ["communication_style"],
        "mirofish_alignment": "contradicts",
        "raw_score": 0.60,
    }

    msg_id_1 = await propose(message_bus, agent_role, content1)
    msg_id_2 = await propose(message_bus, challenger_role, content2)

    transcript = message_bus.get_transcript()
    assert len(transcript) == 2
    assert transcript[0].sender_id == agent_role.agent_id
    assert transcript[1].sender_id == challenger_role.agent_id


@pytest.mark.asyncio
async def test_message_threading_depth(message_bus, agent_role, challenger_role):
    """Test that deep message chains maintain parent_message_id threading."""
    # Create a chain: propose → challenge → reconcile
    proposal_content: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "HIRE",
        "confidence": 0.85,
        "summary": "Good culture fit",
        "key_factors": ["values alignment"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.85,
    }

    proposal_id = await propose(message_bus, agent_role, proposal_content)

    challenge_content: ChallengeContent = {
        "challenger_specialty": "team_dynamics",
        "challenge_type": "assumption",
        "challenge_text": "Need to verify team chemistry",
        "counter_evidence": ["Different work styles"],
        "confidence_impact": -0.10,
    }

    challenge_id = await challenge(
        message_bus, challenger_role, proposal_id, challenge_content
    )

    reconcile_content: ReconciliationContent = {
        "resolution": "partial",
        "updated_recommendation": "HIRE",
        "updated_confidence": 0.80,
        "updated_summary": "Will assess team chemistry carefully",
        "response_to_challenge": "Fair point about team fit",
        "new_evidence": ["Team interviews scheduled"],
        "escalated": False,
    }

    reconcile_id = await reconcile(
        message_bus, agent_role, challenge_id, reconcile_content
    )

    transcript = message_bus.get_transcript()
    assert len(transcript) == 3

    # Verify threading
    assert transcript[0].parent_message_id is None  # Proposal has no parent
    assert transcript[1].parent_message_id == proposal_id  # Challenge parents proposal
    assert transcript[2].parent_message_id == challenge_id  # Reconcile parents challenge


@pytest.mark.asyncio
async def test_proposal_content_shape(message_bus, agent_role):
    """Test that proposal content matches TypedDict contract."""
    content: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "STRONG_HIRE",
        "confidence": 0.92,
        "summary": "Excellent cultural alignment",
        "key_factors": ["values match", "communication style"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.92,
    }

    msg_id = await propose(message_bus, agent_role, content)

    transcript = message_bus.get_transcript()
    msg = transcript[0]

    # Verify all required keys are present
    assert "specialty" in msg.content
    assert "swarm_id" in msg.content
    assert "recommendation" in msg.content
    assert "confidence" in msg.content
    assert "summary" in msg.content
    assert "key_factors" in msg.content
    assert "risk_flags" in msg.content
    assert "mirofish_alignment" in msg.content
    assert "raw_score" in msg.content


@pytest.mark.asyncio
async def test_challenge_content_shape(message_bus, agent_role, challenger_role):
    """Test that challenge content matches TypedDict contract."""
    proposal_content: ProposalContent = {
        "specialty": "culture_fit",
        "swarm_id": "culture_swarm",
        "recommendation": "HIRE",
        "confidence": 0.85,
        "summary": "Good culture fit",
        "key_factors": ["values alignment"],
        "risk_flags": [],
        "mirofish_alignment": "supports",
        "raw_score": 0.85,
    }

    proposal_id = await propose(message_bus, agent_role, proposal_content)

    challenge_content: ChallengeContent = {
        "challenger_specialty": "team_dynamics",
        "challenge_type": "assumption",
        "challenge_text": "Need to verify team chemistry",
        "counter_evidence": ["Different work styles", "Potential friction"],
        "confidence_impact": -0.10,
    }

    challenge_id = await challenge(
        message_bus, challenger_role, proposal_id, challenge_content
    )

    transcript = message_bus.get_transcript()
    challenge_msg = transcript[1]

    # Verify all required keys
    assert "challenger_specialty" in challenge_msg.content
    assert "challenge_type" in challenge_msg.content
    assert "challenge_text" in challenge_msg.content
    assert "counter_evidence" in challenge_msg.content
    assert "confidence_impact" in challenge_msg.content
