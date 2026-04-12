"""
Message Bus for Agent Orchestration

Routes all messages between agents and the orchestrator.
Captures full debate transcript for transparency.

No agent calls another directly. All communication goes through this bus.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages agents can send"""
    PROPOSAL = "proposal"              # Agent proposes initial view
    CHALLENGE = "challenge"             # Agent challenges a proposal
    RECONCILIATION = "reconciliation"   # Agent responds to challenge
    ESCALATION = "escalation"          # Agent requests MiroFish simulation
    ESCALATION_RESULT = "escalation_result"  # Result from MiroFish
    SYNTHESIS = "synthesis"             # Synthesis from orchestrator
    START_DEBATE = "start_debate"       # Orchestrator starts debate
    ELECTION = "election"               # Swarm elects representative
    BOARD_SYNTHESIS = "board_synthesis" # Board presents synthesis


@dataclass
class Message:
    """A message exchanged between agents"""
    sender_id: str              # "orchestrator", "culture_agent", "board", etc.
    message_type: MessageType   # Type of message
    content: Dict[str, Any]     # Structured content
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(uuid4()))
    parent_message_id: Optional[str] = None  # For threading debates

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message"""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "parent_message_id": self.parent_message_id,
        }


@dataclass
class Subscription:
    """Subscription to messages of specific types"""
    agent_id: str
    message_types: List[MessageType]
    callback: Callable


class MessageBus:
    """
    Central message routing hub for agent orchestration.

    Features:
    - Async message send/broadcast
    - Subscription-based routing
    - Full transcript capture (no message lost)
    - Thread-safe operations
    """

    def __init__(self):
        self.subscriptions: Dict[str, List[Subscription]] = {}
        self.transcript: List[Message] = []
        self.pending_messages: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        logger.info("MessageBus initialized")

    async def send(
        self,
        message: Message,
        receivers: Optional[List[str]] = None
    ) -> str:
        """
        Send a message to specific receiver(s).

        Args:
            message: Message to send
            receivers: List of agent IDs to receive. If None, broadcast to all.

        Returns:
            Message ID (for tracking)
        """
        async with self._lock:
            # Log message
            self.transcript.append(message)
            logger.debug(
                f"Message {message.message_id[:8]} from {message.sender_id} "
                f"({message.message_type.value})"
            )

            # Route to subscribers
            if receivers:
                for receiver_id in receivers:
                    await self._route_to_subscriber(message, receiver_id)
            else:
                # Broadcast to all
                for agent_id in self.subscriptions:
                    await self._route_to_subscriber(message, agent_id)

        return message.message_id

    async def broadcast(
        self,
        message: Message,
        receivers: List[str]
    ) -> List[str]:
        """
        Broadcast a message to multiple receivers.

        Returns:
            List of message IDs (one per send)
        """
        message_ids = []
        for receiver in receivers:
            message_ids.append(await self.send(message, [receiver]))
        return message_ids

    async def subscribe(
        self,
        agent_id: str,
        message_types: List[MessageType],
        callback: Optional[Callable] = None
    ) -> str:
        """
        Subscribe an agent to specific message types.

        Args:
            agent_id: Agent identifier
            message_types: Types of messages to subscribe to
            callback: Optional async callback when message arrives

        Returns:
            Subscription ID
        """
        async with self._lock:
            if agent_id not in self.subscriptions:
                self.subscriptions[agent_id] = []

            subscription = Subscription(
                agent_id=agent_id,
                message_types=message_types,
                callback=callback,
            )
            self.subscriptions[agent_id].append(subscription)

            logger.info(
                f"Agent {agent_id} subscribed to {[mt.value for mt in message_types]}"
            )

            return f"{agent_id}_{len(self.subscriptions[agent_id])}"

    async def _route_to_subscriber(self, message: Message, agent_id: str):
        """Internal: Route message to a specific subscriber"""
        if agent_id not in self.subscriptions:
            return

        for subscription in self.subscriptions[agent_id]:
            # Check if agent is subscribed to this message type
            if message.message_type in subscription.message_types:
                if subscription.callback:
                    try:
                        await subscription.callback(message)
                    except Exception as e:
                        logger.error(f"Callback error for {agent_id}: {e}")

    def get_transcript(self) -> List[Message]:
        """Get full debate transcript (all messages)"""
        return self.transcript.copy()

    def get_transcript_dict(self) -> List[Dict[str, Any]]:
        """Get transcript as list of dicts (for serialization)"""
        return [msg.to_dict() for msg in self.transcript]

    def get_messages_from(self, agent_id: str) -> List[Message]:
        """Get all messages from a specific agent"""
        return [msg for msg in self.transcript if msg.sender_id == agent_id]

    def get_messages_of_type(self, message_type: MessageType) -> List[Message]:
        """Get all messages of a specific type"""
        return [msg for msg in self.transcript if msg.message_type == message_type]

    def get_messages_by_parent(self, parent_id: str) -> List[Message]:
        """Get all messages in a debate thread (by parent ID)"""
        return [msg for msg in self.transcript if msg.parent_message_id == parent_id]

    def get_thread(self, root_message_id: str) -> List[Message]:
        """Get full debate thread starting from root message"""
        thread = []
        to_visit = [root_message_id]
        visited = set()

        while to_visit:
            current_id = to_visit.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            # Find message with this ID
            msg = next((m for m in self.transcript if m.message_id == current_id), None)
            if msg:
                thread.append(msg)
                # Find replies (messages with this ID as parent)
                replies = [m for m in self.transcript if m.parent_message_id == current_id]
                to_visit.extend([m.message_id for m in replies])

        return thread

    def get_swarm_consensus(self, swarm_id: str) -> Dict[str, Any]:
        """
        Get consensus from a swarm (all proposals + challenges resolved).

        Returns dict with swarm findings.
        """
        proposals = [
            msg for msg in self.transcript
            if msg.sender_id.endswith(f"_{swarm_id}")
            and msg.message_type == MessageType.PROPOSAL
        ]

        return {
            "swarm_id": swarm_id,
            "proposal_count": len(proposals),
            "proposals": [msg.content for msg in proposals],
        }

    def stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        return {
            "total_messages": len(self.transcript),
            "message_types": {
                mt.value: len([m for m in self.transcript if m.message_type == mt])
                for mt in MessageType
            },
            "agents": list(self.subscriptions.keys()),
            "agent_count": len(self.subscriptions),
        }

    async def clear(self):
        """Clear transcript (for testing)"""
        async with self._lock:
            self.transcript.clear()
