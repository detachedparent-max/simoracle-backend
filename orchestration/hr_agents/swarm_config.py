"""
HR Domain Swarm Configuration

Canonical definition of HR swarms and their agents.
This is the single source of truth passed to Orchestrator.spawn_agents().
"""

from typing import Dict, List

HR_SWARM_CONFIG: Dict[str, List[Dict[str, str]]] = {
    "culture_swarm": [
        {
            "agent_id": "culture_fit_agent",
            "specialty": "culture_fit",
            "instructions": (
                "You assess candidate alignment with company values, "
                "communication style, and leadership philosophy. "
                "Focus on cultural sustainability, not just surface compatibility."
            ),
        },
        {
            "agent_id": "team_dynamics_agent",
            "specialty": "team_dynamics",
            "instructions": (
                "You assess how this candidate complements the existing team. "
                "Evaluate manager fit, team chemistry, and strength distribution."
            ),
        },
    ],
    "skill_swarm": [
        {
            "agent_id": "technical_depth_agent",
            "specialty": "technical_depth",
            "instructions": (
                "You assess technical competency against role requirements. "
                "Evaluate experience depth, cognitive patterns, and execution evidence."
            ),
        },
        {
            "agent_id": "growth_potential_agent",
            "specialty": "growth_potential",
            "instructions": (
                "You assess the candidate's growth trajectory and leadership ceiling. "
                "Evaluate learning velocity, promotability timeline, and role expansion potential."
            ),
        },
    ],
    "retention_swarm": [
        {
            "agent_id": "retention_risk_agent",
            "specialty": "retention_risk",
            "instructions": (
                "You assess the probability that this candidate stays 12-24 months. "
                "Evaluate flight risk, stability signals, and competing-offer likelihood."
            ),
        },
        {
            "agent_id": "market_competitiveness_agent",
            "specialty": "market_competitiveness",
            "instructions": (
                "You assess compensation realism and market demand for this skillset. "
                "Evaluate market benchmark, skill scarcity, and poaching risk timeline."
            ),
        },
    ],
}


def get_hr_swarm_config() -> Dict[str, List[Dict[str, str]]]:
    """Return the canonical HR swarm config."""
    return HR_SWARM_CONFIG


def get_swarm_ids() -> List[str]:
    """Return list of all swarm IDs."""
    return list(HR_SWARM_CONFIG.keys())


def get_agent_ids() -> List[str]:
    """Return flat list of all agent IDs."""
    agent_ids = []
    for agents in HR_SWARM_CONFIG.values():
        for agent in agents:
            agent_ids.append(agent["agent_id"])
    return agent_ids
