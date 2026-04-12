"""
Tests for Orchestrator
"""

import asyncio
import pytest

from orchestration.orchestrator import Orchestrator, DebateDepth, MiroFishSignal


@pytest.fixture
def orchestrator():
    """Create an orchestrator for HR domain"""
    return Orchestrator(domain="hr", shared_api_key="test_key")


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initialization"""
    assert orchestrator.domain == "hr"
    assert orchestrator.shared_api_key == "test_key"
    assert len(orchestrator.agents) == 0
    assert len(orchestrator.swarms) == 0


@pytest.mark.asyncio
async def test_spawn_agents(orchestrator):
    """Test spawning agents"""
    swarm_config = {
        "culture_swarm": [
            {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
            {"agent_id": "team_dynamics_agent", "specialty": "team_dynamics"},
        ],
        "skill_swarm": [
            {"agent_id": "technical_depth_agent", "specialty": "technical_depth"},
            {"agent_id": "growth_potential_agent", "specialty": "growth_potential"},
        ],
    }

    await orchestrator.spawn_agents(swarm_config)

    assert len(orchestrator.agents) == 4
    assert len(orchestrator.swarms) == 2
    assert "culture_fit_agent" in orchestrator.agents
    assert len(orchestrator.swarms["culture_swarm"]) == 2
    assert len(orchestrator.swarms["skill_swarm"]) == 2


@pytest.mark.asyncio
async def test_get_agent(orchestrator):
    """Test retrieving a specific agent"""
    swarm_config = {
        "culture_swarm": [
            {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
        ],
    }

    await orchestrator.spawn_agents(swarm_config)

    agent = orchestrator.get_agent("culture_fit_agent")
    assert agent is not None
    assert agent.agent_id == "culture_fit_agent"
    assert agent.specialty == "culture_fit"
    assert agent.domain == "hr"


@pytest.mark.asyncio
async def test_get_swarm(orchestrator):
    """Test retrieving agents in a swarm"""
    swarm_config = {
        "culture_swarm": [
            {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
            {"agent_id": "team_dynamics_agent", "specialty": "team_dynamics"},
        ],
    }

    await orchestrator.spawn_agents(swarm_config)

    swarm_agents = orchestrator.get_swarm("culture_swarm")
    assert len(swarm_agents) == 2
    assert all(agent.swarm_id == "culture_swarm" for agent in swarm_agents)


@pytest.mark.asyncio
async def test_read_mirofish(orchestrator):
    """Test reading MiroFish signal"""
    question = "Will Jane Doe succeed as Senior PM?"
    context = {"candidate": "Jane Doe", "role": "Senior PM"}

    signal = await orchestrator.read_mirofish(question, context)

    assert signal is not None
    assert 0 <= signal.probability <= 1
    assert 0 <= signal.confidence <= 1
    assert 0 <= signal.agent_diversity <= 1
    assert signal.convergence_rounds > 0


@pytest.mark.asyncio
async def test_assess_signal_full_debate(orchestrator):
    """Test signal assessment with high uncertainty (FULL debate)"""
    # Set up signal with low confidence
    orchestrator.mirofish_signal = MiroFishSignal(
        probability=0.50,
        confidence=0.55,  # Low confidence
        agent_diversity=0.20,
        convergence_rounds=10,
        variance=0.10,
        drift=0.05,
    )

    debate_depth = await orchestrator.assess_signal()
    assert debate_depth == DebateDepth.FULL


@pytest.mark.asyncio
async def test_assess_signal_light_debate(orchestrator):
    """Test signal assessment with moderate uncertainty (LIGHT debate)"""
    orchestrator.mirofish_signal = MiroFishSignal(
        probability=0.72,
        confidence=0.75,  # Moderate confidence
        agent_diversity=0.12,
        convergence_rounds=15,
        variance=0.06,
        drift=0.02,
    )

    debate_depth = await orchestrator.assess_signal()
    assert debate_depth == DebateDepth.LIGHT


@pytest.mark.asyncio
async def test_assess_signal_minimal_debate(orchestrator):
    """Test signal assessment with high confidence (MINIMAL debate)"""
    orchestrator.mirofish_signal = MiroFishSignal(
        probability=0.88,
        confidence=0.89,  # High confidence
        agent_diversity=0.05,  # Low diversity
        convergence_rounds=20,
        variance=0.02,
        drift=0.01,
    )

    debate_depth = await orchestrator.assess_signal()
    assert debate_depth == DebateDepth.MINIMAL


@pytest.mark.asyncio
async def test_delegate_to_board(orchestrator):
    """Test delegation to board"""
    # Set up agents
    swarm_config = {
        "culture_swarm": [
            {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
        ],
    }
    await orchestrator.spawn_agents(swarm_config)

    # Set up MiroFish signal
    orchestrator.mirofish_signal = MiroFishSignal(
        probability=0.72,
        confidence=0.68,
        agent_diversity=0.15,
        convergence_rounds=12,
        variance=0.08,
        drift=0.02,
    )

    question = "Will Jane succeed?"
    context = {"candidate": "Jane"}

    await orchestrator.delegate_to_board(question, context)

    # Check that START_DEBATE message was sent
    transcript = orchestrator.get_transcript()
    assert len(transcript) > 0

    start_msgs = [m for m in transcript if m.message_type.value == "start_debate"]
    assert len(start_msgs) > 0


@pytest.mark.asyncio
async def test_orchestrator_stats(orchestrator):
    """Test orchestrator statistics"""
    swarm_config = {
        "culture_swarm": [
            {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
        ],
    }
    await orchestrator.spawn_agents(swarm_config)

    orchestrator.mirofish_signal = MiroFishSignal(
        probability=0.72,
        confidence=0.68,
        agent_diversity=0.15,
        convergence_rounds=12,
        variance=0.08,
        drift=0.02,
    )

    stats = orchestrator.get_stats()

    assert stats["domain"] == "hr"
    assert stats["agent_count"] == 1
    assert stats["swarm_count"] == 1
    assert stats["mirofish_signal"]["probability"] == 0.72
    assert stats["mirofish_signal"]["confidence"] == 0.68


@pytest.mark.asyncio
async def test_orchestrator_transcript(orchestrator):
    """Test that orchestrator maintains transcript"""
    swarm_config = {
        "culture_swarm": [
            {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
        ],
    }
    await orchestrator.spawn_agents(swarm_config)

    orchestrator.mirofish_signal = MiroFishSignal(
        probability=0.72,
        confidence=0.68,
        agent_diversity=0.15,
        convergence_rounds=12,
        variance=0.08,
        drift=0.02,
    )

    await orchestrator.delegate_to_board(
        question="Test?",
        context={},
    )

    transcript = orchestrator.get_transcript()
    assert len(transcript) > 0


@pytest.mark.asyncio
async def test_full_orchestrator_flow(orchestrator):
    """Test complete orchestrator flow"""
    # 1. Spawn agents
    swarm_config = {
        "culture_swarm": [
            {"agent_id": "culture_fit_agent", "specialty": "culture_fit"},
            {"agent_id": "team_dynamics_agent", "specialty": "team_dynamics"},
        ],
        "skill_swarm": [
            {"agent_id": "technical_depth_agent", "specialty": "technical_depth"},
        ],
    }
    await orchestrator.spawn_agents(swarm_config)
    assert len(orchestrator.agents) == 3

    # 2. Read MiroFish signal
    question = "Will Jane Doe succeed as Senior PM?"
    context = {
        "candidate": "Jane Doe",
        "role": "Senior PM",
        "years_experience": 8,
    }
    signal = await orchestrator.read_mirofish(question, context)
    assert signal is not None

    # 3. Assess signal (decide debate depth)
    debate_depth = await orchestrator.assess_signal()
    assert debate_depth in [DebateDepth.MINIMAL, DebateDepth.LIGHT, DebateDepth.FULL]

    # 4. Delegate to board
    await orchestrator.delegate_to_board(question, context)

    # 5. Check stats
    stats = orchestrator.get_stats()
    assert stats["agent_count"] == 3
    assert stats["debate_depth"] == debate_depth.value

    # 6. Check transcript
    transcript = orchestrator.get_transcript()
    assert len(transcript) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
