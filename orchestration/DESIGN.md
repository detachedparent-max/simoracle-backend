# SimOracle Agent Orchestration Framework

## Phase 2 Design Document

**Status**: Design phase (ready for implementation)  
**Domain**: HR (first oracle)  
**Target**: 2-3 week implementation  

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CUSTOMER REQUEST                          │
│         (Question + Candidate Data + Domain)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  ORCHESTRATOR (Entry)       │
        │  - Validates request        │
        │  - Spawns MiroFish          │
        │  - Reads signal strength    │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  SIGNAL ASSESSMENT          │
        │  - Probability confidence   │
        │  - Agent diversity          │
        │  - Variance / convergence   │
        │  → Decide debate depth      │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  AGENT BOARD (Conditional)  │
        │  - Sub-swarms debate        │
        │  - Due diligence            │
        │  - Optional MiroFish loops  │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  ORCHESTRATOR (Synthesis)   │
        │  - Weighs inputs            │
        │  - Resolves conflicts       │
        │  - Final signal             │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  TRANSCRIPT BUILDER         │
        │  - Full debate record       │
        │  - Reasoning layers         │
        │  - Confidence trajectory    │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  INSTRUMENT PANEL FORMATTER │
        │  - Structured output        │
        │  - Non-LLM prose            │
        │  - Telemetry + metadata     │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    CUSTOMER OUTPUT          │
        │  (Proprietary Panel)        │
        └─────────────────────────────┘
```

---

## 2. Core Components

### 2.1 Message Bus (`message_bus.py`)

**Purpose**: Route messages between agents and orchestrator. No agent directly calls another; all communication goes through the bus.

**Key interfaces**:
```python
class Message:
    sender_id: str          # "orchestrator", "culture_agent", etc.
    receiver_id: str        # "board", "skill_agent", etc.
    message_type: str       # "proposal", "challenge", "question", "synthesis"
    content: Dict[str, Any] # Structured data
    timestamp: datetime
    parent_message_id: Optional[str]  # For threading debates

class MessageBus:
    async def send(message: Message) -> str  # Returns message_id
    async def broadcast(message: Message, receivers: List[str]) -> List[str]
    async def subscribe(agent_id: str, message_types: List[str]) -> Callable
    def transcript() -> List[Message]  # Full debate record
```

**Behavior**:
- All messages are logged (transcript building)
- Messages are routed based on agent subscriptions
- No message is lost (persistent in-memory queue for this session)
- Agents don't block on responses (async, non-blocking)

---

### 2.2 Agent Registry (`orchestrator.py`)

**Purpose**: Track all active agents, their roles, and responsibilities.

```python
@dataclass
class AgentRole:
    agent_id: str
    domain: str              # "hr", "mna", "real_estate"
    specialty: str           # "culture_fit", "skill_depth", "retention_risk", etc.
    swarm_id: str           # "culture_swarm", "skill_swarm", etc.
    api_key: Optional[str]  # Customer's API key (shared context)
    instructions: str       # Role-specific system prompt

class Orchestrator:
    def __init__(self, domain: str, shared_api_key: str):
        self.domain = domain
        self.shared_api_key = shared_api_key
        self.agents: Dict[str, AgentRole] = {}
        self.message_bus = MessageBus()
        self.mirofish_signal: Optional[MiroFishSignal] = None
        self.debate_depth: str = "unknown"  # "minimal", "light", "full"
        self.transcript: List[Message] = []
    
    async def spawn_agents(self, swarm_config: Dict):
        """Initialize agents based on domain and swarm config"""
        ...
    
    async def read_mirofish(self, question: str, customer_data: Dict):
        """Poll MiroFish, assess signal strength, decide debate depth"""
        ...
    
    async def delegate_to_board(self):
        """Orchestrator tells board to begin due diligence"""
        ...
    
    async def synthesize(self):
        """Orchestrator reads all agent input, makes final call"""
        ...
```

---

### 2.3 Agent Board (`agent_board.py`)

**Purpose**: Coordinate sub-swarms, elect representatives, present findings to orchestrator.

```python
class AgentBoard:
    def __init__(self, orchestrator: Orchestrator, message_bus: MessageBus):
        self.orchestrator = orchestrator
        self.message_bus = message_bus
        self.swarms: Dict[str, SubSwarm] = {}
        self.representatives: Dict[str, AgentRole] = {}
    
    async def run_swarm_debate(self, swarm_id: str, mirofish_signal: Dict):
        """Each swarm debates internally, produces consensus"""
        ...
    
    async def elect_representatives(self):
        """Each swarm picks one agent to present to board"""
        ...
    
    async def board_synthesis_round(self):
        """Representatives present, board debates trade-offs"""
        ...

class SubSwarm:
    def __init__(self, swarm_id: str, agents: List[AgentRole]):
        self.swarm_id = swarm_id
        self.agents = agents
    
    async def internal_debate(self, mirofish_signal: Dict) -> SwarmConsensus:
        """Agents argue, produce consensus view + minority opinions"""
        ...
```

---

### 2.4 Debate Protocol (`debate_protocol.py`)

**Purpose**: Define how agents argue, challenge, reconcile.

**Flow**:

1. **Proposal Phase** (Agent reads MiroFish, proposes interpretation)
   ```
   Agent A → Message Bus:
   {
       "type": "proposal",
       "specialty": "culture_fit",
       "proposal": "Strong alignment with company values",
       "confidence": 0.89,
       "reasoning": "..."
   }
   ```

2. **Challenge Phase** (Other agents in swarm challenge)
   ```
   Agent B → Message Bus:
   {
       "type": "challenge",
       "parent_message_id": "...",
       "challenge": "Assumption about remote-first culture needs validation",
       "counter_evidence": "..."
   }
   ```

3. **Due Diligence** (Agent decides: accept challenge, loop back to MiroFish, or defend)
   ```
   Agent A → MiroFish (optional):
   "Run simulation with constraint: candidate remote-first work preference"
   
   Agent A → Message Bus:
   {
       "type": "reconciliation",
       "parent_message_id": "...",
       "resolution": "Challenge valid; refined estimate to 0.82",
       "new_evidence": "..."
   }
   ```

4. **Synthesis** (Orchestrator collects all, produces final view)

**Implementation**:
```python
async def propose(agent: AgentRole, message: Message):
    """Agent makes initial proposal based on MiroFish + domain expertise"""
    await message_bus.send(message)

async def challenge(agent: AgentRole, parent_id: str, challenge: str):
    """Agent challenges proposal with counterargument"""
    ...

async def reconcile(agent: AgentRole, parent_id: str, resolution: str):
    """Agent responds to challenge, may loop to MiroFish"""
    ...

async def escalate_to_mirofish(agent: AgentRole, question: str) -> MiroFishSignal:
    """Agent requests additional simulation to resolve uncertainty"""
    # Use shared API key
    # Document in transcript as "(Agent escalated to simulation)"
    ...
```

---

### 2.5 HR Domain Agents (`hr_agents/`)

**Four swarms** (first pass; can add more):

#### **Culture & Fit Swarm**
- **Culture Fit Agent**: "Does candidate align with company values?"
- **Team Dynamics Agent**: "How does this candidate complement existing team?"

#### **Skill & Trajectory Swarm**
- **Technical Depth Agent**: "Does candidate have required technical skills?"
- **Growth Potential Agent**: "Can candidate grow into expanded role?"

#### **Retention & Risk Swarm**
- **Retention Risk Agent**: "Will candidate stay 18-24 months?"
- **Market Competitiveness Agent**: "Is compensation competitive for this market?"

#### **Board Synthesizer** (Optional)
- **Executive Summary Agent**: "Cross-domain synthesis + final recommendation"

**Each agent has**:
- System prompt (role-specific)
- Domain expertise patterns
- Confidence calibration rules
- Escalation triggers (when to loop back to MiroFish)

---

### 2.6 Transcript Builder (`transcript_builder.py`)

**Purpose**: Capture full debate record, formatted for customer visibility.

```python
class TranscriptBuilder:
    def __init__(self, orchestrator: Orchestrator, message_bus: MessageBus):
        self.orchestrator = orchestrator
        self.message_bus = message_bus
    
    def build_transcript(self) -> Transcript:
        """
        Returns structured transcript with:
        - Orchestrator's initial signal assessment
        - Each swarm's internal debate
        - Representative presentations
        - Board-level trade-offs
        - Orchestrator's final synthesis
        - Any escalations to MiroFish (documented)
        - Confidence trajectory across phases
        """
        return Transcript(
            phases=[
                TranscriptPhase.mirofish_assessment,
                TranscriptPhase.swarm_debates,
                TranscriptPhase.board_synthesis,
                TranscriptPhase.orchestrator_final,
            ],
            messages=self.message_bus.transcript(),
            confidence_trajectory=self._build_confidence_trajectory(),
            escalations=self._extract_escalations(),
        )

@dataclass
class Transcript:
    phases: List[TranscriptPhase]
    messages: List[Message]
    confidence_trajectory: List[ConfidencePoint]
    escalations: List[MiroFishEscalation]
```

---

## 3. Request Flow (Step by Step)

### **Request In**
```python
result = await orchestrator.process(
    question="Should we hire Alice Chen for Senior Engineer role?",
    domain="hr",
    candidate_data={
        "name": "Alice Chen",
        "experience_years": 8,
        "culture_fit_score": 0.91,
        "interview_feedback": "...",
        ...
    },
    context={...}
)
```

### **Step 1: Orchestrator Spawns Agents**
```python
await orchestrator.spawn_agents(
    domain="hr",
    swarm_config={
        "culture_swarm": ["culture_fit_agent", "team_dynamics_agent"],
        "skill_swarm": ["technical_depth_agent", "growth_potential_agent"],
        "retention_swarm": ["retention_risk_agent", "market_competitiveness_agent"],
    }
)
```

### **Step 2: Orchestrator Reads MiroFish**
```python
self.mirofish_signal = await mirofish.get_probability(
    question=question,
    domain="hr",
    context=candidate_data
)
# Returns: probability=0.79, confidence=0.72, diversity=0.18, convergence_rounds=15
```

### **Step 3: Orchestrator Assesses Signal**
```python
self.debate_depth = orchestrator._assess_debate_depth(
    probability=0.79,
    confidence=0.72,
    diversity=0.18,
    convergence=15
)
# Returns: "full" (confidence < 0.80, so agents should dig in)
```

### **Step 4: Orchestrator Delegates**
```python
await message_bus.broadcast(
    Message(
        sender_id="orchestrator",
        receiver_id="board",
        message_type="start_debate",
        content={
            "mirofish_signal": self.mirofish_signal,
            "debate_depth": "full",
            "question": question,
            "candidate_data": candidate_data,
        }
    ),
    receivers=["culture_swarm", "skill_swarm", "retention_swarm"]
)
```

### **Step 5: Sub-Swarms Debate**
```
# Culture Swarm:
Culture Fit Agent: "Alice shows strong alignment with transparency, execution values"
Team Dynamics Agent: "Complements existing team strengths in async collaboration"

# Skill Swarm:
Technical Agent: "8yrs experience exceeds role requirements. Can lead subteam in 18mo."
Growth Agent: "Growth trajectory supports 2-year leadership progression"

# Retention Swarm:
Retention Agent: "Market hot for this skillset. 18mo retention: 71%. Flight risk if better offer."
Market Agent: "Current comp $185K below benchmark $210K. Poaching likely within 6mo."

# Each agent can optionally escalate to MiroFish for more specific scenarios:
# E.g., Retention Agent: "Run simulation: candidate receives competing offer in 6 months"
```

### **Step 6: Board Representatives Present**
Each swarm elects a representative to present findings to board.

### **Step 7: Board Debates Trade-Offs**
Representatives argue trade-offs across domains (culture vs. retention risk, etc.)

### **Step 8: Orchestrator Synthesizes**
```python
final_position = await orchestrator.synthesize(
    mirofish_signal=self.mirofish_signal,
    swarm_inputs=await message_bus.collect_swarm_findings(),
    board_synthesis=await agent_board.get_synthesis(),
)
# Orchestrator can agree or disagree with board
# Produces final probability, confidence, recommendation
```

### **Step 9: Transcript Built**
```python
transcript = await transcript_builder.build_transcript()
# Full record of:
# - MiroFish signal
# - Each agent's reasoning
# - Challenges raised
# - Evidence loops to MiroFish
# - Final synthesis
```

### **Step 10: Instrument Panel Formatted**
```python
panel = await instrument_panel_formatter.format(
    transcript=transcript,
    mirofish_signal=self.mirofish_signal,
    final_position=final_position,
)
# Returns structured, non-LLM output (see example in simoracle_agent_debate_framework.md)
```

### **Result Out**
Customer sees proprietary instrument panel with:
- Primary recommendation (STRONG HIRE, etc.)
- Simulation stack (MiroFish baseline + agent refinements)
- Reasoning layers (L1-L5)
- Factor map (visual table)
- Swarm debate summary (full text)
- Decision matrix
- Risk surface
- Confidence trajectory
- Conditions and mitigations

---

## 4. Key Design Patterns

### **Pattern 1: Shared API Context**
- Customer provides one API key
- All agents share this context (no key-per-agent overhead)
- Message bus tracks usage for billing

### **Pattern 2: Conditional Debate**
```python
def _assess_debate_depth(mirofish_signal):
    confidence = mirofish_signal.confidence
    diversity = mirofish_signal.agent_diversity
    
    if confidence >= 0.85 and diversity < 0.10:
        return "minimal"  # Signal is clear, skip debate
    elif confidence >= 0.70:
        return "light"    # Some uncertainty, quick due diligence
    else:
        return "full"     # High uncertainty, full debate
```

### **Pattern 3: Escalation Loop**
Agents can escalate to MiroFish mid-debate for confidence refinement:
```python
async def escalate_to_mirofish(agent: AgentRole, scenario: str):
    """Run additional simulation for specific scenario"""
    new_signal = await mirofish.get_probability(
        question=original_question,
        context={**original_context, "constraint": scenario}
    )
    # Document escalation in transcript
    await message_bus.send(Message(
        sender_id=agent.agent_id,
        message_type="escalation_result",
        content={"scenario": scenario, "new_signal": new_signal}
    ))
```

### **Pattern 4: Confidence Trajectory**
Track confidence across phases:
- Phase 1 (MiroFish initial): confidence = 0.72
- Phase 2 (Swarm debate): confidence = 0.84
- Phase 3 (Board synthesis): confidence = 0.87
- Phase 4 (Orchestrator final): confidence = 0.87 (stable)

Shows how debate increases confidence.

---

## 5. Domain-Agnostic Framework

Same orchestration logic for all domains. Only the swarm config changes:

### **HR Domain**
```python
SWARMS = {
    "culture": ["culture_fit_agent", "team_dynamics_agent"],
    "skill": ["technical_depth_agent", "growth_agent"],
    "retention": ["retention_risk_agent", "market_competitiveness_agent"],
}
```

### **M&A Domain**
```python
SWARMS = {
    "financial": ["valuation_agent", "synergy_agent"],
    "legal": ["regulatory_agent", "due_diligence_agent"],
    "cultural": ["integration_risk_agent"],
    "market": ["competitive_position_agent"],
    "execution": ["execution_risk_agent"],
}
```

### **Real Estate Domain**
```python
SWARMS = {
    "valuation": ["market_comp_agent", "valuation_model_agent"],
    "market": ["demand_agent", "macro_trends_agent"],
    "tenant": ["credit_risk_agent", "lease_stability_agent"],
    "regulatory": ["zoning_agent", "compliance_agent"],
    "macro": ["interest_rate_agent", "macro_economic_agent"],
}
```

Same orchestrator, same debate protocol, different agents.

---

## 6. Implementation Roadmap

### **Week 1: Core Infrastructure**
- [ ] Message bus (`message_bus.py`)
- [ ] Orchestrator scaffold (`orchestrator.py`)
- [ ] Agent registry and roles
- [ ] Basic agent interface
- [ ] MiroFish signal assessment logic

### **Week 2: HR Swarms & Debate Protocol**
- [ ] Culture swarm (2 agents)
- [ ] Skill swarm (2 agents)
- [ ] Retention swarm (2 agents)
- [ ] Debate protocol (propose → challenge → reconcile)
- [ ] Escalation logic (agent → MiroFish loop)
- [ ] Swarm election (representative selection)

### **Week 3: Synthesis & Output**
- [ ] Orchestrator synthesis logic
- [ ] Transcript builder
- [ ] Instrument panel formatter
- [ ] Confidence trajectory tracking
- [ ] End-to-end HR test case

### **Testing**
- [ ] Unit tests for message bus
- [ ] Unit tests for debate protocol
- [ ] Integration test: full HR hiring scenario
- [ ] Manual test: compare against actual hiring decisions

---

## 7. File Structure

```
/Users/thikay/simoracle-backend/orchestration/
├── __init__.py
├── DESIGN.md (this file)
├── message_bus.py           # Message routing + transcript
├── orchestrator.py          # Main orchestrator, agent registry
├── agent_board.py           # Board coordination, swarm hierarchy
├── debate_protocol.py       # Propose/challenge/reconcile flow
├── transcript_builder.py    # Debate record formatter
├── hr_agents/
│   ├── __init__.py
│   ├── culture_fit_agent.py
│   ├── team_dynamics_agent.py
│   ├── technical_depth_agent.py
│   ├── growth_potential_agent.py
│   ├── retention_risk_agent.py
│   ├── market_competitiveness_agent.py
│   └── swarm_config.py      # HR-specific swarm definitions
├── mna_agents/              # (Future)
├── real_estate_agents/      # (Future)
└── output/                  # (Phase 3)
    ├── instrument_panel.py
    ├── formatting/
    └── telemetry/
```

---

## 8. Success Criteria

**Week 1 Complete**: Message bus working, basic orchestrator spawning agents, MiroFish signal assessment deciding debate depth.

**Week 2 Complete**: All 6 HR agents implemented, debate flowing (propose → challenge), agents can escalate to MiroFish and document it.

**Week 3 Complete**: Full HR scenario working end-to-end, transcript captured, instrument panel formatted and readable.

**Quality Gate**: 
- Run 10 historical HR hiring decisions through orchestrator
- Compare final recommendation against actual hiring outcome
- Verify debate logic added value (caught risks MiroFish alone missed)
- Verify confidence trajectory makes sense (increases through debate)

---

This design is:
- **Domain-agnostic** (swap swarms, keep orchestrator)
- **Extensible** (add agents, add swarms, add domains)
- **Transparent** (full transcript visible to customer)
- **Conditional** (debate depth based on signal confidence)
- **Loopable** (agents can escalate to MiroFish mid-debate)
- **Scalable** (message bus handles hundreds of agents)

Ready for implementation.
