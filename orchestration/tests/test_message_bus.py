"""
Tests for MessageBus
"""

import asyncio
import pytest

from orchestration.message_bus import MessageBus, Message, MessageType


@pytest.fixture
def message_bus():
    """Create a fresh message bus for each test"""
    return MessageBus()


@pytest.mark.asyncio
async def test_send_message(message_bus):
    """Test sending a single message"""
    msg = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "strong culture fit"},
    )

    msg_id = await message_bus.send(msg)

    assert msg_id == msg.message_id
    assert len(message_bus.get_transcript()) == 1
    assert message_bus.get_transcript()[0].sender_id == "agent_a"


@pytest.mark.asyncio
async def test_broadcast_message(message_bus):
    """Test broadcasting a message to multiple receivers"""
    msg = Message(
        sender_id="orchestrator",
        message_type=MessageType.START_DEBATE,
        content={"question": "test"},
    )

    # Subscribe receivers
    await message_bus.subscribe("agent_a", [MessageType.START_DEBATE])
    await message_bus.subscribe("agent_b", [MessageType.START_DEBATE])

    msg_ids = await message_bus.broadcast(msg, ["agent_a", "agent_b"])

    assert len(msg_ids) == 2
    assert len(message_bus.get_transcript()) == 1  # Same message, multiple sends


@pytest.mark.asyncio
async def test_subscribe_agent(message_bus):
    """Test agent subscription"""
    called = []

    async def callback(msg):
        called.append(msg)

    sub_id = await message_bus.subscribe(
        "agent_a",
        [MessageType.PROPOSAL],
        callback=callback,
    )

    assert sub_id is not None
    assert "agent_a" in message_bus.subscriptions


@pytest.mark.asyncio
async def test_message_routing_to_subscriber(message_bus):
    """Test that messages are routed to subscribers"""
    received = []

    async def callback(msg):
        received.append(msg)

    await message_bus.subscribe(
        "agent_a",
        [MessageType.PROPOSAL],
        callback=callback,
    )

    msg = Message(
        sender_id="agent_b",
        message_type=MessageType.PROPOSAL,
        content={"claim": "test"},
    )

    await message_bus.send(msg, ["agent_a"])

    # Give callback time to execute
    await asyncio.sleep(0.1)

    assert len(received) == 1
    assert received[0].content["claim"] == "test"


@pytest.mark.asyncio
async def test_message_type_filtering(message_bus):
    """Test that agents only receive subscribed message types"""
    received = []

    async def callback(msg):
        received.append(msg)

    # Subscribe only to PROPOSAL
    await message_bus.subscribe(
        "agent_a",
        [MessageType.PROPOSAL],
        callback=callback,
    )

    # Send PROPOSAL (should receive)
    proposal = Message(
        sender_id="agent_b",
        message_type=MessageType.PROPOSAL,
        content={"claim": "test"},
    )
    await message_bus.send(proposal, ["agent_a"])

    # Send CHALLENGE (should NOT receive)
    challenge = Message(
        sender_id="agent_c",
        message_type=MessageType.CHALLENGE,
        content={"challenge": "test"},
    )
    await message_bus.send(challenge, ["agent_a"])

    await asyncio.sleep(0.1)

    assert len(received) == 1  # Only the PROPOSAL


@pytest.mark.asyncio
async def test_transcript_capture(message_bus):
    """Test that full transcript is captured"""
    msg1 = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "A"},
    )
    msg2 = Message(
        sender_id="agent_b",
        message_type=MessageType.CHALLENGE,
        content={"challenge": "B"},
        parent_message_id=msg1.message_id,
    )
    msg3 = Message(
        sender_id="agent_a",
        message_type=MessageType.RECONCILIATION,
        content={"resolution": "C"},
        parent_message_id=msg2.message_id,
    )

    await message_bus.send(msg1)
    await message_bus.send(msg2)
    await message_bus.send(msg3)

    transcript = message_bus.get_transcript()
    assert len(transcript) == 3
    assert transcript[0].message_type == MessageType.PROPOSAL
    assert transcript[1].message_type == MessageType.CHALLENGE
    assert transcript[2].message_type == MessageType.RECONCILIATION


@pytest.mark.asyncio
async def test_get_messages_from_agent(message_bus):
    """Test filtering messages by sender"""
    msg1 = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "A"},
    )
    msg2 = Message(
        sender_id="agent_b",
        message_type=MessageType.PROPOSAL,
        content={"claim": "B"},
    )
    msg3 = Message(
        sender_id="agent_a",
        message_type=MessageType.CHALLENGE,
        content={"challenge": "C"},
    )

    await message_bus.send(msg1)
    await message_bus.send(msg2)
    await message_bus.send(msg3)

    agent_a_messages = message_bus.get_messages_from("agent_a")
    assert len(agent_a_messages) == 2
    assert all(m.sender_id == "agent_a" for m in agent_a_messages)


@pytest.mark.asyncio
async def test_get_messages_of_type(message_bus):
    """Test filtering messages by type"""
    msg1 = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "A"},
    )
    msg2 = Message(
        sender_id="agent_b",
        message_type=MessageType.CHALLENGE,
        content={"challenge": "B"},
    )
    msg3 = Message(
        sender_id="agent_c",
        message_type=MessageType.PROPOSAL,
        content={"claim": "C"},
    )

    await message_bus.send(msg1)
    await message_bus.send(msg2)
    await message_bus.send(msg3)

    proposals = message_bus.get_messages_of_type(MessageType.PROPOSAL)
    assert len(proposals) == 2
    assert all(m.message_type == MessageType.PROPOSAL for m in proposals)


@pytest.mark.asyncio
async def test_get_thread(message_bus):
    """Test retrieving a full debate thread"""
    root = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "A"},
    )
    challenge = Message(
        sender_id="agent_b",
        message_type=MessageType.CHALLENGE,
        content={"challenge": "B"},
        parent_message_id=root.message_id,
    )
    reconciliation = Message(
        sender_id="agent_a",
        message_type=MessageType.RECONCILIATION,
        content={"resolution": "C"},
        parent_message_id=challenge.message_id,
    )

    await message_bus.send(root)
    await message_bus.send(challenge)
    await message_bus.send(reconciliation)

    thread = message_bus.get_thread(root.message_id)
    assert len(thread) == 3
    assert thread[0].message_type == MessageType.PROPOSAL


@pytest.mark.asyncio
async def test_message_bus_stats(message_bus):
    """Test statistics reporting"""
    await message_bus.subscribe("agent_a", [MessageType.PROPOSAL])
    await message_bus.subscribe("agent_b", [MessageType.CHALLENGE])

    msg1 = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "A"},
    )
    msg2 = Message(
        sender_id="agent_b",
        message_type=MessageType.CHALLENGE,
        content={"challenge": "B"},
    )

    await message_bus.send(msg1)
    await message_bus.send(msg2)

    stats = message_bus.stats()
    assert stats["total_messages"] == 2
    assert stats["agent_count"] == 2
    assert stats["message_types"][MessageType.PROPOSAL.value] == 1
    assert stats["message_types"][MessageType.CHALLENGE.value] == 1


@pytest.mark.asyncio
async def test_message_serialization(message_bus):
    """Test message serialization to dict"""
    msg = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "test"},
    )

    await message_bus.send(msg)

    transcript_dict = message_bus.get_transcript_dict()
    assert len(transcript_dict) == 1
    assert transcript_dict[0]["sender_id"] == "agent_a"
    assert transcript_dict[0]["message_type"] == "proposal"
    assert transcript_dict[0]["content"]["claim"] == "test"


@pytest.mark.asyncio
async def test_clear_transcript(message_bus):
    """Test clearing transcript"""
    msg = Message(
        sender_id="agent_a",
        message_type=MessageType.PROPOSAL,
        content={"claim": "test"},
    )

    await message_bus.send(msg)
    assert len(message_bus.get_transcript()) == 1

    await message_bus.clear()
    assert len(message_bus.get_transcript()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
