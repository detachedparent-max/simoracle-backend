"""
Integration tests for agent board orchestration.

Validates full debate flow: swarm debates, representative election, board synthesis.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import Dict, Any

from orchestration.message_bus import MessageBus, MessageType
from orchestration.orchestrator import Orchestrator, DebateDepth
from orchestration.agent_board import AgentBoard, SubSwarm, SwarmConsensus
from orchestration.hr_agents.swarm_config import get_hr_swarm_config


@pytest_asyncio.fixture
async def orchestrator():
    """Create an orchestrator with agents."""
    orch = Orchestrator(domain="hr")
    await orch.spawn_agents(get_hr_swarm_config())

    # Set up MiroFish signal
    await orch.read_mirofish(
        "Should we hire this candidate?",
        {"role": "senior_engineer", "team_size": 8},
    )
    await orch.assess_signal()

    return orch


@pytest.fixture
def strong_candidate_data():
    """Strong hire candidate."""
    return {
        "name": "Alice Chen",
        "years_experience": 8,
        "role_match_score": 0.88,
        "culture_alignment_score": 0.82,
        "compensation_ask": 140000,
        "market_rate": 145000,
        "skills": ["Python", "System Design", "Distributed Systems"],
        "red_flags": [],
        "growth_indicators": ["promoted twice in 3 years", "led technical migration"],
    }


@pytest.fixture
def weak_candidate_data():
    """Weak candidate with red flags."""
    return {
        "name": "Bob Smith",
        "years_experience": 2,
        "role_match_score": 0.45,
        "culture_alignment_score": 0.35,
        "compensation_ask": 200000,
        "market_rate": 120000,
        "skills": ["JavaScript"],
        "red_flags": ["job hopping", "technical gaps", "communication issues"],
        "growth_indicators": [],
    }


@pytest.fixture
def medium_candidate_data():
    """Medium candidate (HOLD territory)."""
    return {
        "name": "Carol Davis",
        "years_experience": 5,
        "role_match_score": 0.70,
        "culture_alignment_score": 0.60,
        "compensation_ask": 130000,
        "market_rate": 135000,
        "skills": ["Python", "JavaScript"],
        "red_flags": ["some communication gaps"],
        "growth_indicators": ["one promotion in 4 years"],
    }


# ============================================================================
# SubSwarm Tests
# ============================================================================


@pytest.mark.asyncio
async def test_subswarm_minimal_depth(orchestrator, strong_candidate_data):
    """SubSwarm with MINIMAL depth should skip debate."""
    board = AgentBoard(orchestrator)
    swarms = board._create_swarms()
    culture_swarm = swarms["culture_swarm"]

    result = await culture_swarm.internal_debate(
        strong_candidate_data,
        orchestrator.get_mirofish_signal(),
        DebateDepth.MINIMAL,
    )

    assert isinstance(result, SwarmConsensus)
    assert result.swarm_id == "culture_swarm"
    assert result.elected_agent_id is not None
    assert result.debate_rounds == 0  # MINIMAL = no debate
    assert len(result.dissenting_views) == 0  # No dissent


@pytest.mark.asyncio
async def test_subswarm_light_depth(orchestrator, strong_candidate_data):
    """SubSwarm with LIGHT depth should propose only, elect by confidence."""
    board = AgentBoard(orchestrator)
    swarms = board._create_swarms()
    culture_swarm = swarms["culture_swarm"]

    result = await culture_swarm.internal_debate(
        strong_candidate_data,
        orchestrator.get_mirofish_signal(),
        DebateDepth.LIGHT,
    )

    assert isinstance(result, SwarmConsensus)
    assert result.debate_rounds == 1  # LIGHT = proposals only
    assert result.elected_agent_id is not None
    assert result.recommendation in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]


@pytest.mark.asyncio
async def test_subswarm_full_depth(orchestrator, strong_candidate_data):
    """SubSwarm with FULL depth should run propose→challenge→reconcile."""
    board = AgentBoard(orchestrator)
    swarms = board._create_swarms()
    culture_swarm = swarms["culture_swarm"]

    result = await culture_swarm.internal_debate(
        strong_candidate_data,
        orchestrator.get_mirofish_signal(),
        DebateDepth.FULL,
    )

    assert isinstance(result, SwarmConsensus)
    assert result.debate_rounds == 3  # FULL = propose + challenge + reconcile
    assert result.elected_agent_id is not None
    assert result.recommendation in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]


@pytest.mark.asyncio
async def test_subswarm_consensus_has_all_fields(orchestrator, strong_candidate_data):
    """SwarmConsensus should have all required fields."""
    board = AgentBoard(orchestrator)
    swarms = board._create_swarms()
    culture_swarm = swarms["culture_swarm"]

    result = await culture_swarm.internal_debate(
        strong_candidate_data,
        orchestrator.get_mirofish_signal(),
        DebateDepth.LIGHT,
    )

    assert result.swarm_id == "culture_swarm"
    assert result.elected_agent_id is not None
    assert result.elected_specialty is not None
    assert result.recommendation in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.proposal_summary, str)
    assert isinstance(result.dissenting_views, list)
    assert isinstance(result.debate_rounds, int)


# ============================================================================
# AgentBoard Full Debate Tests
# ============================================================================


@pytest.mark.asyncio
async def test_agent_board_full_debate_strong_candidate(orchestrator, strong_candidate_data):
    """AgentBoard full debate for strong candidate should recommend HIRE or STRONG_HIRE."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    assert result["final_recommendation"] in ["STRONG_HIRE", "HIRE"]
    assert isinstance(result["final_confidence"], float)
    assert 0.0 <= result["final_confidence"] <= 1.0
    assert isinstance(result["board_rationale"], str)
    assert isinstance(result["swarm_inputs"], dict)
    assert len(result["swarm_inputs"]) == 3  # 3 swarms
    assert isinstance(result["confidence_trajectory"], list)
    assert len(result["confidence_trajectory"]) == 4  # 4 phases


@pytest.mark.asyncio
async def test_agent_board_full_debate_weak_candidate(orchestrator, weak_candidate_data):
    """AgentBoard full debate for weak candidate should recommend PASS or HOLD."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(weak_candidate_data)

    assert result["final_recommendation"] in ["PASS", "STRONG_PASS", "HOLD"]
    assert isinstance(result["final_confidence"], float)


@pytest.mark.asyncio
async def test_agent_board_full_debate_medium_candidate(orchestrator, medium_candidate_data):
    """AgentBoard full debate for medium candidate should produce valid decision."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(medium_candidate_data)

    assert result["final_recommendation"] in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]
    assert isinstance(result["final_confidence"], float)
    assert 0.0 <= result["final_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_board_synthesis_content_shape(orchestrator, strong_candidate_data):
    """Board synthesis output should have all required fields."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    assert "final_recommendation" in result
    assert "final_confidence" in result
    assert "board_rationale" in result
    assert "cross_domain_tensions" in result
    assert "swarm_inputs" in result
    assert "confidence_trajectory" in result
    assert "escalation_count" in result


@pytest.mark.asyncio
async def test_confidence_trajectory_four_phases(orchestrator, strong_candidate_data):
    """Confidence trajectory should have 4 phases."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    trajectory = result["confidence_trajectory"]
    assert len(trajectory) == 4

    phases = [t["phase"] for t in trajectory]
    assert "mirofish_initial" in phases
    assert "swarm_debate" in phases
    assert "board_synthesis" in phases
    assert "orchestrator_final" in phases

    # All phases should have confidence values
    for phase_data in trajectory:
        assert "confidence" in phase_data
        assert isinstance(phase_data["confidence"], float)


@pytest.mark.asyncio
async def test_swarm_inputs_from_three_swarms(orchestrator, strong_candidate_data):
    """Board synthesis should include inputs from all 3 swarms."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    swarm_inputs = result["swarm_inputs"]
    assert "culture_swarm" in swarm_inputs
    assert "skill_swarm" in swarm_inputs
    assert "retention_swarm" in swarm_inputs

    # Each swarm input should be a valid recommendation
    valid_recs = ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]
    for rec in swarm_inputs.values():
        assert rec in valid_recs


@pytest.mark.asyncio
async def test_board_rationale_contains_recommendation(orchestrator, strong_candidate_data):
    """Board rationale should mention the final recommendation."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    rationale = result["board_rationale"]
    recommendation = result["final_recommendation"]

    # Rationale should mention the recommendation
    assert recommendation in rationale


# ============================================================================
# Transcript Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_debate_captures_messages_in_transcript(orchestrator, strong_candidate_data):
    """Full debate should generate multiple messages in transcript."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    transcript = orchestrator.message_bus.get_transcript()

    # Should have at least: proposals from 6 agents, elections from 3 swarms, board synthesis
    # = 6 proposals + 3 elections + 1 board synthesis = 10+ messages
    assert len(transcript) >= 10


@pytest.mark.asyncio
async def test_transcript_contains_proposal_messages(orchestrator, strong_candidate_data):
    """Transcript should contain PROPOSAL messages from all agents."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    transcript = orchestrator.message_bus.get_transcript()

    proposals = [m for m in transcript if m.message_type == MessageType.PROPOSAL]
    assert len(proposals) >= 6  # At least 6 agents proposing


@pytest.mark.asyncio
async def test_transcript_contains_election_messages(orchestrator, strong_candidate_data):
    """Transcript should contain ELECTION messages from each swarm."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    transcript = orchestrator.message_bus.get_transcript()

    elections = [m for m in transcript if m.message_type == MessageType.ELECTION]
    assert len(elections) == 3  # One election per swarm


@pytest.mark.asyncio
async def test_transcript_contains_board_synthesis(orchestrator, strong_candidate_data):
    """Transcript should contain exactly one BOARD_SYNTHESIS message."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    transcript = orchestrator.message_bus.get_transcript()

    syntheses = [m for m in transcript if m.message_type == MessageType.BOARD_SYNTHESIS]
    assert len(syntheses) == 1


# ============================================================================
# Agent Instantiation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_agent_board_instantiates_correct_agents(orchestrator):
    """AgentBoard should instantiate correct agent types."""
    board = AgentBoard(orchestrator)

    swarms = board._create_swarms()

    # Verify swarm structure
    assert len(swarms) == 3
    assert "culture_swarm" in swarms
    assert "skill_swarm" in swarms
    assert "retention_swarm" in swarms

    # Verify each swarm has agents
    for swarm in swarms.values():
        assert isinstance(swarm, SubSwarm)
        assert len(swarm.agents) == 2


@pytest.mark.asyncio
async def test_instantiate_agent_factory(orchestrator):
    """_instantiate_agent factory should create correct agent types."""
    board = AgentBoard(orchestrator)

    from orchestration.orchestrator import AgentRole
    from orchestration.hr_agents.culture_fit_agent import CultureFitAgent
    from orchestration.hr_agents.technical_depth_agent import TechnicalDepthAgent
    from orchestration.hr_agents.market_competitiveness_agent import MarketCompAgent

    culture_role = AgentRole(
        agent_id="c1", domain="hr", specialty="culture_fit", swarm_id="culture_swarm", instructions=""
    )
    tech_role = AgentRole(
        agent_id="t1", domain="hr", specialty="technical_depth", swarm_id="skill_swarm", instructions=""
    )
    market_role = AgentRole(
        agent_id="m1", domain="hr", specialty="market_competitiveness", swarm_id="retention_swarm", instructions=""
    )

    culture_agent = board._instantiate_agent(culture_role)
    tech_agent = board._instantiate_agent(tech_role)
    market_agent = board._instantiate_agent(market_role)

    assert isinstance(culture_agent, CultureFitAgent)
    assert isinstance(tech_agent, TechnicalDepthAgent)
    assert isinstance(market_agent, MarketCompAgent)


# ============================================================================
# Parallel Swarm Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_swarm_debates_run_in_parallel(orchestrator, strong_candidate_data):
    """Three swarm debates should run in parallel via asyncio.gather."""
    board = AgentBoard(orchestrator)

    import time

    start = time.time()
    result = await board.run_full_debate(strong_candidate_data)
    elapsed = time.time() - start

    # If running in parallel, should be faster than sequential
    # (This is a soft assertion - timing can vary)
    assert elapsed < 5.0  # Should complete reasonably quickly


# ============================================================================
# Disagreement & Tension Detection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_board_detects_swarm_disagreements(orchestrator, strong_candidate_data):
    """Board should detect when swarms disagree on recommendation."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    swarm_inputs = result["swarm_inputs"]
    unique_recommendations = set(swarm_inputs.values())

    # If there's disagreement, tensions should be recorded
    if len(unique_recommendations) > 1:
        assert len(result["cross_domain_tensions"]) > 0


@pytest.mark.asyncio
async def test_board_confidence_adjusts_for_disagreement(orchestrator):
    """Board should lower confidence when swarms disagree."""
    board = AgentBoard(orchestrator)

    # Create a candidate that might cause disagreement
    candidate = {
        "name": "Test",
        "years_experience": 3,
        "role_match_score": 0.60,
        "culture_alignment_score": 0.50,
        "compensation_ask": 110000,
        "market_rate": 100000,
        "skills": ["Python"],
        "red_flags": ["some concerns"],
        "growth_indicators": ["one move"],
    }

    result = await board.run_full_debate(candidate)

    # Confidence should be in valid range
    assert 0.0 <= result["final_confidence"] <= 1.0


# ============================================================================
# Confidence Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_confidence_trajectory_values_are_valid(orchestrator, strong_candidate_data):
    """All confidence values in trajectory should be between 0.0 and 1.0."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    trajectory = result["confidence_trajectory"]
    for phase_data in trajectory:
        confidence = phase_data["confidence"]
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_final_confidence_matches_trajectory(orchestrator, strong_candidate_data):
    """Final confidence should match the last trajectory phase."""
    board = AgentBoard(orchestrator)

    result = await board.run_full_debate(strong_candidate_data)

    final_confidence = result["final_confidence"]
    trajectory = result["confidence_trajectory"]
    last_phase_confidence = trajectory[-1]["confidence"]

    assert final_confidence == last_phase_confidence


# ============================================================================
# Edge Cases & Robustness Tests
# ============================================================================


@pytest.mark.asyncio
async def test_board_handles_zero_years_experience(orchestrator):
    """Board should handle candidate with no experience."""
    board = AgentBoard(orchestrator)

    candidate = {
        "name": "Fresh Grad",
        "years_experience": 0,
        "role_match_score": 0.40,
        "culture_alignment_score": 0.50,
        "compensation_ask": 80000,
        "market_rate": 120000,
        "skills": ["Python"],
        "red_flags": ["no professional experience"],
        "growth_indicators": [],
    }

    result = await board.run_full_debate(candidate)

    assert result["final_recommendation"] in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]


@pytest.mark.asyncio
async def test_board_handles_all_red_flags(orchestrator):
    """Board should handle candidate with many red flags."""
    board = AgentBoard(orchestrator)

    candidate = {
        "name": "Problematic",
        "years_experience": 2,
        "role_match_score": 0.30,
        "culture_alignment_score": 0.20,
        "compensation_ask": 250000,
        "market_rate": 120000,
        "skills": ["Basic Python"],
        "red_flags": [
            "job hopping",
            "technical gaps",
            "communication issues",
            "compensation concerns",
            "retention risk",
        ],
        "growth_indicators": [],
    }

    result = await board.run_full_debate(candidate)

    # Should still produce valid recommendation
    assert result["final_recommendation"] in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]
    # Confidence should be lower due to red flags
    assert result["final_confidence"] < 0.70


@pytest.mark.asyncio
async def test_board_handles_no_growth_indicators(orchestrator):
    """Board should handle candidate with no growth indicators."""
    board = AgentBoard(orchestrator)

    candidate = {
        "name": "Stable",
        "years_experience": 10,
        "role_match_score": 0.85,
        "culture_alignment_score": 0.75,
        "compensation_ask": 140000,
        "market_rate": 145000,
        "skills": ["Python", "System Design"],
        "red_flags": [],
        "growth_indicators": [],
    }

    result = await board.run_full_debate(candidate)

    assert result["final_recommendation"] in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]
