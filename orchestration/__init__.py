"""
SimOracle Agent Orchestration Framework

Public API for Phase 2 (Agent Board) + Phase 3 (ODE) + Phase 4 (Output)

This module provides:
- Message bus (agent routing + transcript)
- Orchestrator (entry point, agent registry)
- Agent board (hierarchical debate)
- Organizational decision engine (policy-driven decisions)
- Instrument panel formatter (proprietary output)
"""

from .message_bus import MessageBus, Message, MessageType
from .orchestrator import Orchestrator, DebateDepth, MiroFishSignal, AgentRole

__all__ = [
    "MessageBus",
    "Message",
    "MessageType",
    "Orchestrator",
    "DebateDepth",
    "MiroFishSignal",
    "AgentRole",
]

__version__ = "0.1.0"
