"""
Transcript Builder

Converts MessageBus transcript into human-readable debate record.
Formats messages into hierarchical conversation threads with timestamps.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .message_bus import Message, MessageType

logger = logging.getLogger(__name__)


class DebateThread:
    """A threaded conversation (proposal + challenges + reconciliations)."""

    def __init__(self, proposal_msg: Message):
        self.proposal = proposal_msg
        self.challenges: List[Message] = []
        self.reconciliations: List[Message] = []

    def add_challenge(self, challenge_msg: Message):
        """Add challenge message to thread."""
        self.challenges.append(challenge_msg)

    def add_reconciliation(self, reconciliation_msg: Message):
        """Add reconciliation message to thread."""
        self.reconciliations.append(reconciliation_msg)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize thread."""
        return {
            "proposal": self.proposal.to_dict(),
            "challenges": [c.to_dict() for c in self.challenges],
            "reconciliations": [r.to_dict() for r in self.reconciliations],
        }


class TranscriptBuilder:
    """Builds readable transcript from message bus transcript."""

    def __init__(self, messages: List[Message]):
        """
        Initialize transcript builder.

        Args:
            messages: Full transcript from MessageBus.transcript
        """
        self.messages = messages
        self.threads: Dict[str, DebateThread] = {}
        self.elections: List[Message] = []
        self.synthesis: Optional[Message] = None
        self._build_threads()

    def _build_threads(self):
        """Parse messages into debate threads."""
        proposal_map: Dict[str, DebateThread] = {}

        for msg in self.messages:
            if msg.message_type == MessageType.PROPOSAL:
                thread = DebateThread(msg)
                proposal_map[msg.message_id] = thread
                self.threads[msg.message_id] = thread

            elif msg.message_type == MessageType.CHALLENGE:
                parent_id = msg.parent_message_id
                if parent_id and parent_id in proposal_map:
                    proposal_map[parent_id].add_challenge(msg)

            elif msg.message_type == MessageType.RECONCILIATION:
                parent_id = msg.parent_message_id
                if parent_id and parent_id in proposal_map:
                    proposal_map[parent_id].add_reconciliation(msg)

            elif msg.message_type == MessageType.ELECTION:
                self.elections.append(msg)

            elif msg.message_type == MessageType.BOARD_SYNTHESIS:
                self.synthesis = msg

    def get_debate_tree(self) -> Dict[str, Any]:
        """
        Return nested debate tree structure.

        Returns:
            {
                "threads": [
                    {
                        "proposal": {...},
                        "challenges": [{...}],
                        "reconciliations": [{...}]
                    }
                ],
                "elections": [{...}],
                "synthesis": {...}
            }
        """
        return {
            "threads": [thread.to_dict() for thread in self.threads.values()],
            "elections": [e.to_dict() for e in self.elections],
            "synthesis": self.synthesis.to_dict() if self.synthesis else None,
        }

    def get_formatted_text(self) -> str:
        """
        Return human-readable debate transcript.

        Returns:
            Formatted text report of debate flow
        """
        lines = []
        lines.append("=" * 80)
        lines.append("AGENT DEBATE TRANSCRIPT")
        lines.append("=" * 80)

        # Phase 1: Proposals
        lines.append("\n### PHASE 1: INITIAL PROPOSALS ###\n")
        for i, thread in enumerate(self.threads.values(), 1):
            proposal = thread.proposal.content
            lines.append(f"[{i}] {proposal.get('specialty', 'unknown').upper()}")
            lines.append(f"    Recommendation: {proposal.get('recommendation', 'N/A')}")
            lines.append(f"    Confidence: {proposal.get('confidence', 0):.0%}")
            lines.append(f"    Summary: {proposal.get('summary', 'N/A')}")
            lines.append(f"    Key Factors:")
            for factor in proposal.get("key_factors", []):
                lines.append(f"      • {factor}")
            if proposal.get("risk_flags"):
                lines.append(f"    Risk Flags:")
                for flag in proposal.get("risk_flags", []):
                    lines.append(f"      • {flag}")
            lines.append("")

        # Phase 2: Challenges
        if any(thread.challenges for thread in self.threads.values()):
            lines.append("\n### PHASE 2: CHALLENGES ###\n")
            challenge_count = 1
            for thread in self.threads.values():
                for challenge in thread.challenges:
                    content = challenge.content
                    lines.append(
                        f"[{challenge_count}] {content.get('challenger_specialty', 'unknown').upper()} "
                        f"challenges {thread.proposal.content.get('specialty', 'unknown').upper()}"
                    )
                    lines.append(f"    Type: {content.get('challenge_type', 'N/A')}")
                    lines.append(f"    Challenge: {content.get('challenge_text', 'N/A')}")
                    lines.append(f"    Counter-Evidence:")
                    for evidence in content.get("counter_evidence", []):
                        lines.append(f"      • {evidence}")
                    lines.append(
                        f"    Confidence Impact: {content.get('confidence_impact', 0):+.0%}"
                    )
                    lines.append("")
                    challenge_count += 1

        # Phase 3: Reconciliations
        if any(thread.reconciliations for thread in self.threads.values()):
            lines.append("\n### PHASE 3: RECONCILIATIONS ###\n")
            recon_count = 1
            for thread in self.threads.values():
                for recon in thread.reconciliations:
                    content = recon.content
                    lines.append(
                        f"[{recon_count}] {thread.proposal.content.get('specialty', 'unknown').upper()} "
                        f"responds to challenge"
                    )
                    lines.append(f"    Resolution: {content.get('resolution', 'N/A')}")
                    lines.append(
                        f"    Updated Confidence: {content.get('updated_confidence', 0):.0%}"
                    )
                    lines.append(f"    Response: {content.get('response_to_challenge', 'N/A')}")
                    if content.get("new_evidence"):
                        lines.append(f"    New Evidence:")
                        for evidence in content.get("new_evidence", []):
                            lines.append(f"      • {evidence}")
                    lines.append("")
                    recon_count += 1

        # Phase 4: Elections
        if self.elections:
            lines.append("\n### PHASE 4: SWARM ELECTIONS ###\n")
            for i, election in enumerate(self.elections, 1):
                content = election.content
                lines.append(f"[{i}] {content.get('swarm_id', 'unknown').upper()}")
                lines.append(
                    f"    Elected: {content.get('elected_specialty', 'N/A')} "
                    f"({content.get('elected_agent_id', 'N/A')})"
                )
                lines.append(f"    Winning Confidence: {content.get('winning_confidence', 0):.0%}")
                lines.append(f"    Election Reason: {content.get('election_reason', 'N/A')}")
                if content.get("dissenting_views"):
                    lines.append(f"    Dissenting Views:")
                    for view in content.get("dissenting_views", []):
                        lines.append(f"      • {view}")
                lines.append("")

        # Phase 5: Board Synthesis
        if self.synthesis:
            lines.append("\n### PHASE 5: BOARD SYNTHESIS ###\n")
            content = self.synthesis.content
            lines.append(f"Final Recommendation: {content.get('final_recommendation', 'N/A')}")
            lines.append(f"Final Confidence: {content.get('final_confidence', 0):.0%}")
            lines.append(f"\nBoard Rationale:")
            lines.append(f"  {content.get('board_rationale', 'N/A')}")

            if content.get("cross_domain_tensions"):
                lines.append(f"\nCross-Domain Tensions:")
                for tension in content.get("cross_domain_tensions", []):
                    lines.append(f"  • {tension}")

            if content.get("swarm_inputs"):
                lines.append(f"\nSwarm Inputs:")
                for swarm_id, inputs in content.get("swarm_inputs", {}).items():
                    lines.append(f"  {swarm_id}: {inputs}")

            if content.get("confidence_trajectory"):
                lines.append(f"\nConfidence Trajectory:")
                for phase_data in content.get("confidence_trajectory", []):
                    lines.append(
                        f"  {phase_data.get('phase', 'N/A')}: {phase_data.get('confidence', 0):.0%}"
                    )

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)

    def summary_stats(self) -> Dict[str, Any]:
        """
        Return summary statistics about debate.

        Returns:
            {
                "total_messages": int,
                "proposal_count": int,
                "challenge_count": int,
                "reconciliation_count": int,
                "election_count": int,
                "debate_phases": int,
                "total_confidence_change": float,
            }
        """
        proposal_count = len(self.threads)
        challenge_count = sum(
            len(thread.challenges) for thread in self.threads.values()
        )
        reconciliation_count = sum(
            len(thread.reconciliations) for thread in self.threads.values()
        )
        election_count = len(self.elections)

        # Calculate confidence change
        total_initial_confidence = sum(
            thread.proposal.content.get("confidence", 0)
            for thread in self.threads.values()
        )
        final_confidence = (
            self.synthesis.content.get("final_confidence", 0) if self.synthesis else 0
        )

        # Count phases with content
        phases = 1  # Always have proposals
        if challenge_count > 0:
            phases += 1
        if reconciliation_count > 0:
            phases += 1
        if election_count > 0:
            phases += 1
        if self.synthesis:
            phases += 1

        return {
            "total_messages": len(self.messages),
            "proposal_count": proposal_count,
            "challenge_count": challenge_count,
            "reconciliation_count": reconciliation_count,
            "election_count": election_count,
            "debate_phases": phases,
            "final_confidence": final_confidence,
        }
