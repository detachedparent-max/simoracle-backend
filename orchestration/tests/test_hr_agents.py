"""
Tests for HR agents.

Validates that each agent generates valid proposals, challenges, and reconciliations
with specialty-specific stub logic.
"""

import pytest
from typing import Dict, Any

from orchestration.message_bus import MessageBus
from orchestration.orchestrator import AgentRole, MiroFishSignal
from orchestration.hr_agents import HRAgent
from orchestration.hr_agents.culture_fit_agent import CultureFitAgent
from orchestration.hr_agents.team_dynamics_agent import TeamDynamicsAgent
from orchestration.hr_agents.technical_depth_agent import TechnicalDepthAgent
from orchestration.hr_agents.growth_potential_agent import GrowthPotentialAgent
from orchestration.hr_agents.retention_risk_agent import RetentionRiskAgent
from orchestration.hr_agents.market_competitiveness_agent import MarketCompAgent


@pytest.fixture
def message_bus():
    return MessageBus()


@pytest.fixture
def mirofish_signal():
    return MiroFishSignal(
        probability=0.75,
        confidence=0.85,
        agent_diversity=0.70,
        convergence_rounds=5,
        variance=0.10,
        drift=0.02,
        narrative="Test signal",
    )


@pytest.fixture
def culture_fit_role():
    return AgentRole(
        agent_id="culture_fit_agent_1",
        domain="hr",
        specialty="culture_fit",
        swarm_id="culture_swarm",
        instructions="Assess cultural alignment",
    )


@pytest.fixture
def team_dynamics_role():
    return AgentRole(
        agent_id="team_dynamics_agent_1",
        domain="hr",
        specialty="team_dynamics",
        swarm_id="culture_swarm",
        instructions="Assess team fit",
    )


@pytest.fixture
def technical_depth_role():
    return AgentRole(
        agent_id="technical_depth_agent_1",
        domain="hr",
        specialty="technical_depth",
        swarm_id="skill_swarm",
        instructions="Assess technical skills",
    )


@pytest.fixture
def growth_potential_role():
    return AgentRole(
        agent_id="growth_potential_agent_1",
        domain="hr",
        specialty="growth_potential",
        swarm_id="skill_swarm",
        instructions="Assess growth trajectory",
    )


@pytest.fixture
def retention_risk_role():
    return AgentRole(
        agent_id="retention_risk_agent_1",
        domain="hr",
        specialty="retention_risk",
        swarm_id="retention_swarm",
        instructions="Assess retention risk",
    )


@pytest.fixture
def market_comp_role():
    return AgentRole(
        agent_id="market_comp_agent_1",
        domain="hr",
        specialty="market_competitiveness",
        swarm_id="retention_swarm",
        instructions="Assess compensation competitiveness",
    )


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


# ============================================================================
# CultureFitAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_culture_fit_strong_candidate(
    message_bus, culture_fit_role, mirofish_signal, strong_candidate_data
):
    """CultureFitAgent should recommend HIRE/STRONG_HIRE for high culture alignment."""
    agent = CultureFitAgent(culture_fit_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "culture_fit"
    assert proposal["swarm_id"] == "culture_swarm"
    assert proposal["recommendation"] in ["HIRE", "STRONG_HIRE"]
    assert proposal["confidence"] >= 0.75
    assert "summary" in proposal
    assert "key_factors" in proposal


@pytest.mark.asyncio
async def test_culture_fit_weak_candidate(
    message_bus, culture_fit_role, mirofish_signal, weak_candidate_data
):
    """CultureFitAgent should recommend PASS for low culture alignment."""
    agent = CultureFitAgent(culture_fit_role, message_bus)
    proposal = await agent.generate_proposal(weak_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "culture_fit"
    assert proposal["recommendation"] in ["PASS", "STRONG_PASS", "HOLD"]
    assert proposal["confidence"] <= 0.50


@pytest.mark.asyncio
async def test_culture_fit_challenge(
    message_bus, culture_fit_role, team_dynamics_role, mirofish_signal, strong_candidate_data
):
    """CultureFitAgent should generate valid challenges."""
    agent = CultureFitAgent(culture_fit_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    challenge = await agent.generate_challenge(proposal, strong_candidate_data)

    assert "challenger_specialty" in challenge
    assert challenge["challenge_type"] in ["assumption", "missing_data", "counter_evidence"]
    assert "challenge_text" in challenge
    assert "counter_evidence" in challenge
    assert "confidence_impact" in challenge


@pytest.mark.asyncio
async def test_culture_fit_reconciliation(
    message_bus, culture_fit_role, mirofish_signal, strong_candidate_data
):
    """CultureFitAgent should generate valid reconciliations."""
    agent = CultureFitAgent(culture_fit_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    challenge = await agent.generate_challenge(proposal, strong_candidate_data)

    reconciliation = await agent.generate_reconciliation(
        challenge, proposal, strong_candidate_data
    )

    assert "resolution" in reconciliation
    assert reconciliation["resolution"] in ["accepted", "partial", "defended"]
    assert "updated_confidence" in reconciliation
    assert "response_to_challenge" in reconciliation


# ============================================================================
# TechnicalDepthAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_technical_depth_strong_candidate(
    message_bus, technical_depth_role, mirofish_signal, strong_candidate_data
):
    """TechnicalDepthAgent should recommend HIRE/STRONG_HIRE for high tech match."""
    agent = TechnicalDepthAgent(technical_depth_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "technical_depth"
    assert proposal["swarm_id"] == "skill_swarm"
    assert proposal["recommendation"] in ["HIRE", "STRONG_HIRE"]
    assert proposal["confidence"] >= 0.70


@pytest.mark.asyncio
async def test_technical_depth_weak_candidate(
    message_bus, technical_depth_role, mirofish_signal, weak_candidate_data
):
    """TechnicalDepthAgent should recommend PASS for low tech match."""
    agent = TechnicalDepthAgent(technical_depth_role, message_bus)
    proposal = await agent.generate_proposal(weak_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "technical_depth"
    assert proposal["recommendation"] in ["PASS", "STRONG_PASS"]


@pytest.mark.asyncio
async def test_technical_depth_challenge(
    message_bus, technical_depth_role, mirofish_signal, strong_candidate_data
):
    """TechnicalDepthAgent should generate valid challenges."""
    agent = TechnicalDepthAgent(technical_depth_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    challenge = await agent.generate_challenge(proposal, strong_candidate_data)

    assert "challenge_type" in challenge
    assert "challenge_text" in challenge
    assert "confidence_impact" in challenge


# ============================================================================
# GrowthPotentialAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_growth_potential_strong_candidate(
    message_bus, growth_potential_role, mirofish_signal, strong_candidate_data
):
    """GrowthPotentialAgent should recommend HIRE/STRONG_HIRE for high growth."""
    agent = GrowthPotentialAgent(growth_potential_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "growth_potential"
    assert proposal["swarm_id"] == "skill_swarm"
    assert proposal["recommendation"] in ["HIRE", "STRONG_HIRE"]


@pytest.mark.asyncio
async def test_growth_potential_weak_candidate(
    message_bus, growth_potential_role, mirofish_signal, weak_candidate_data
):
    """GrowthPotentialAgent should recommend PASS for minimal growth."""
    agent = GrowthPotentialAgent(growth_potential_role, message_bus)
    proposal = await agent.generate_proposal(weak_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "growth_potential"
    assert proposal["recommendation"] in ["HOLD", "PASS"]


# ============================================================================
# RetentionRiskAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_retention_risk_strong_candidate(
    message_bus, retention_risk_role, mirofish_signal, strong_candidate_data
):
    """RetentionRiskAgent should recommend HIRE/STRONG_HIRE for low flight risk."""
    agent = RetentionRiskAgent(retention_risk_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "retention_risk"
    assert proposal["swarm_id"] == "retention_swarm"
    assert proposal["recommendation"] in ["HIRE", "STRONG_HIRE"]
    assert proposal["confidence"] >= 0.70


@pytest.mark.asyncio
async def test_retention_risk_weak_candidate(
    message_bus, retention_risk_role, mirofish_signal, weak_candidate_data
):
    """RetentionRiskAgent should recommend PASS for high flight risk."""
    agent = RetentionRiskAgent(retention_risk_role, message_bus)
    proposal = await agent.generate_proposal(weak_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "retention_risk"
    assert proposal["recommendation"] in ["HOLD", "PASS"]


# ============================================================================
# MarketCompAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_market_comp_below_market(
    message_bus, market_comp_role, mirofish_signal, strong_candidate_data
):
    """MarketCompAgent should recommend STRONG_HIRE for below-market offers."""
    agent = MarketCompAgent(market_comp_role, message_bus)
    candidate = {**strong_candidate_data, "compensation_ask": 130000, "market_rate": 145000}
    proposal = await agent.generate_proposal(candidate, mirofish_signal)

    assert proposal["specialty"] == "market_competitiveness"
    assert proposal["swarm_id"] == "retention_swarm"
    assert proposal["recommendation"] in ["STRONG_HIRE", "HIRE"]
    assert proposal["confidence"] >= 0.80


@pytest.mark.asyncio
async def test_market_comp_above_market(
    message_bus, market_comp_role, mirofish_signal, weak_candidate_data
):
    """MarketCompAgent should recommend PASS for above-market asks."""
    agent = MarketCompAgent(market_comp_role, message_bus)
    proposal = await agent.generate_proposal(weak_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "market_competitiveness"
    assert proposal["recommendation"] in ["PASS", "STRONG_PASS"]
    assert proposal["confidence"] <= 0.40


@pytest.mark.asyncio
async def test_market_comp_challenge(
    message_bus, market_comp_role, mirofish_signal, strong_candidate_data
):
    """MarketCompAgent should generate valid challenges."""
    agent = MarketCompAgent(market_comp_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    challenge = await agent.generate_challenge(proposal, strong_candidate_data)

    assert "challenge_type" in challenge
    assert "challenge_text" in challenge
    assert "confidence_impact" in challenge


# ============================================================================
# TeamDynamicsAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_team_dynamics_strong_candidate(
    message_bus, team_dynamics_role, mirofish_signal, strong_candidate_data
):
    """TeamDynamicsAgent should generate valid proposals."""
    agent = TeamDynamicsAgent(team_dynamics_role, message_bus)
    proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)

    assert proposal["specialty"] == "team_dynamics"
    assert proposal["swarm_id"] == "culture_swarm"
    assert proposal["recommendation"] in ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]
    assert 0.0 <= proposal["confidence"] <= 1.0


# ============================================================================
# Agent Properties Tests
# ============================================================================


@pytest.mark.asyncio
async def test_agent_properties(message_bus, culture_fit_role):
    """Test that agents have correct properties."""
    agent = CultureFitAgent(culture_fit_role, message_bus)

    assert agent.agent_id == culture_fit_role.agent_id
    assert agent.specialty == "culture_fit"
    assert agent.swarm_id == "culture_swarm"


@pytest.mark.asyncio
async def test_all_agents_have_correct_swarm_ids(message_bus):
    """Test that agents are assigned to correct swarms."""
    culture_role = AgentRole(
        agent_id="culture_1", domain="hr", specialty="culture_fit", swarm_id="culture_swarm", instructions=""
    )
    team_role = AgentRole(
        agent_id="team_1", domain="hr", specialty="team_dynamics", swarm_id="culture_swarm", instructions=""
    )
    tech_role = AgentRole(
        agent_id="tech_1", domain="hr", specialty="technical_depth", swarm_id="skill_swarm", instructions=""
    )
    growth_role = AgentRole(
        agent_id="growth_1", domain="hr", specialty="growth_potential", swarm_id="skill_swarm", instructions=""
    )
    retention_role = AgentRole(
        agent_id="retention_1", domain="hr", specialty="retention_risk", swarm_id="retention_swarm", instructions=""
    )
    market_role = AgentRole(
        agent_id="market_1", domain="hr", specialty="market_competitiveness", swarm_id="retention_swarm", instructions=""
    )

    culture_agent = CultureFitAgent(culture_role, message_bus)
    team_agent = TeamDynamicsAgent(team_role, message_bus)
    tech_agent = TechnicalDepthAgent(tech_role, message_bus)
    growth_agent = GrowthPotentialAgent(growth_role, message_bus)
    retention_agent = RetentionRiskAgent(retention_role, message_bus)
    market_agent = MarketCompAgent(market_role, message_bus)

    assert culture_agent.swarm_id == "culture_swarm"
    assert team_agent.swarm_id == "culture_swarm"
    assert tech_agent.swarm_id == "skill_swarm"
    assert growth_agent.swarm_id == "skill_swarm"
    assert retention_agent.swarm_id == "retention_swarm"
    assert market_agent.swarm_id == "retention_swarm"


# ============================================================================
# Recommendation Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_all_proposals_have_valid_recommendations(
    message_bus, mirofish_signal, strong_candidate_data
):
    """Test that all agents produce valid recommendations."""
    valid_recommendations = ["STRONG_HIRE", "HIRE", "HOLD", "PASS", "STRONG_PASS"]

    culture_agent = CultureFitAgent(
        AgentRole(agent_id="c1", domain="hr", specialty="culture_fit", swarm_id="culture_swarm", instructions=""), message_bus
    )
    team_agent = TeamDynamicsAgent(
        AgentRole(agent_id="t1", domain="hr", specialty="team_dynamics", swarm_id="culture_swarm", instructions=""), message_bus
    )
    tech_agent = TechnicalDepthAgent(
        AgentRole(agent_id="te1", domain="hr", specialty="technical_depth", swarm_id="skill_swarm", instructions=""), message_bus
    )
    growth_agent = GrowthPotentialAgent(
        AgentRole(agent_id="g1", domain="hr", specialty="growth_potential", swarm_id="skill_swarm", instructions=""), message_bus
    )
    retention_agent = RetentionRiskAgent(
        AgentRole(agent_id="r1", domain="hr", specialty="retention_risk", swarm_id="retention_swarm", instructions=""), message_bus
    )
    market_agent = MarketCompAgent(
        AgentRole(agent_id="m1", domain="hr", specialty="market_competitiveness", swarm_id="retention_swarm", instructions=""), message_bus
    )

    agents = [culture_agent, team_agent, tech_agent, growth_agent, retention_agent, market_agent]

    for agent in agents:
        proposal = await agent.generate_proposal(strong_candidate_data, mirofish_signal)
        assert proposal["recommendation"] in valid_recommendations
        assert 0.0 <= proposal["confidence"] <= 1.0


# ============================================================================
# Red Flag Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_culture_fit_penalizes_communication_red_flags(message_bus, culture_fit_role, mirofish_signal):
    """CultureFitAgent should lower confidence for communication red flags."""
    agent = CultureFitAgent(culture_fit_role, message_bus)

    clean_candidate = {
        "name": "Alice",
        "years_experience": 5,
        "role_match_score": 0.8,
        "culture_alignment_score": 0.80,
        "compensation_ask": 100000,
        "market_rate": 100000,
        "skills": ["Python"],
        "red_flags": [],
        "growth_indicators": [],
    }

    flagged_candidate = {**clean_candidate, "red_flags": ["communication issues", "conflict"]}

    clean_proposal = await agent.generate_proposal(clean_candidate, mirofish_signal)
    flagged_proposal = await agent.generate_proposal(flagged_candidate, mirofish_signal)

    # Confidence should be lower when red flags present
    assert flagged_proposal["confidence"] <= clean_proposal["confidence"]


@pytest.mark.asyncio
async def test_technical_depth_penalizes_skill_red_flags(message_bus, technical_depth_role, mirofish_signal):
    """TechnicalDepthAgent should lower confidence for skill red flags."""
    agent = TechnicalDepthAgent(technical_depth_role, message_bus)

    clean_candidate = {
        "name": "Bob",
        "years_experience": 5,
        "role_match_score": 0.80,
        "culture_alignment_score": 0.70,
        "compensation_ask": 100000,
        "market_rate": 100000,
        "skills": ["Python", "System Design"],
        "red_flags": [],
        "growth_indicators": [],
    }

    flagged_candidate = {**clean_candidate, "red_flags": ["technical gaps", "outdated skills"]}

    clean_proposal = await agent.generate_proposal(clean_candidate, mirofish_signal)
    flagged_proposal = await agent.generate_proposal(flagged_candidate, mirofish_signal)

    assert flagged_proposal["confidence"] <= clean_proposal["confidence"]
