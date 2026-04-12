# SimOracle Orchestration Architecture — LOCKED IN

**Status**: Final architecture specification, ready for implementation  
**Phase**: 2 (Agent Orchestration + ODE) + Phase 3 (Output Formatting)  
**Target**: 5 weeks, 1 complete HR oracle, billion-dollar ready  

---

## Executive Summary

SimOracle is a **four-layer reasoning system** that replaces entire organizational decision-making departments:

1. **MiroFish** — Raw simulations (probability oracle)
2. **Agent Board** — Hierarchical debate (reasoning layer)
3. **Instrument Panel** — Structured output (reporting layer)
4. **Organizational Decision Engine (ODE)** — Policy + decision authority (decision layer)

The **ODE is the moat.** It's not just "smart." It's accountable, policy-driven, and enterprise-ready.

---

## Architecture (Four Layers)

### **Layer 1: MiroFish Simulations**

**Input**: Question + domain context  
**Output**: `MiroFishSignal`

```python
@dataclass
class MiroFishSignal:
    probability: float           # 0-1, the core prediction
    confidence: float            # 0-1, how sure are we?
    agent_diversity: float       # 0-1, do agents agree?
    convergence_rounds: int      # How many rounds to stabilize?
    variance: float              # Spread of agent outputs
    drift: float                 # Movement across rounds
```

**Status**: Exists. Can run in parallel with debate. Will be wired into ODE at decision time.

---

### **Layer 2: Agent Board (Hierarchical Debate)**

**Input**: MiroFishSignal + candidate/role/company data  
**Output**: `DebateTranscript` + `BoardSynthesis`

**Structure**:
- **Sub-swarms** (domain-specific agents debate internally)
  - Culture Swarm: 2 agents (culture fit, team dynamics)
  - Skill Swarm: 2 agents (technical depth, growth potential)
  - Retention Swarm: 2 agents (retention risk, market competitiveness)
- **Board** (representatives present, board debates trade-offs)
- **Transcript** (full debate record, all messages captured)

**Flow**:
1. Orchestrator reads MiroFish signal
2. Decides debate depth: minimal / light / full
3. Delegates to sub-swarms
4. Sub-swarms debate (propose → challenge → reconcile)
5. Agents optionally escalate to MiroFish for more data
6. Representatives elected, board debate happens
7. Transcript captured with full reasoning chain

**Implementation**: `orchestration/` module  
- `message_bus.py` — Message routing + transcript capture
- `orchestrator.py` — Entry point, agent registry, signal assessment
- `agent_board.py` — Board coordination, swarm hierarchy
- `debate_protocol.py` — Propose/challenge/reconcile flow
- `hr_agents/` — 6 HR-specific agents
- `transcript_builder.py` — Debate record formatter

**Status**: To be built (Phase 2, Weeks 1-3)

---

### **Layer 3: Instrument Panel (Structured Output)**

**Input**: MiroFishSignal + DebateTranscript + BoardSynthesis  
**Output**: `InstrumentPanel` (proprietary, non-LLM formatted)

**Format**:
- Primary recommendation (STRONG HIRE, ADVANCE, FLAG, REJECT)
- Simulation stack (baseline + refinements)
- Reasoning layers (L1-L5)
- Factor map (visual table of drivers)
- Swarm debate summaries (full text from each swarm)
- Decision matrix (quantitative summary)
- Risk surface (identified risks + mitigations)
- Confidence trajectory (across debate phases)
- Conditions and next actions

**Example**: See `simoracle_agent_debate_framework.md`

**Implementation**: `orchestration/output/`
- `instrument_panel.py` — Panel generator
- `formatting/` — Structured output builders
- `telemetry/` — Metadata, version, timestamps

**Status**: To be built (Phase 3, Weeks 4-5)

---

### **Layer 4: Organizational Decision Engine (ODE)**

**The Lead Orchestrator is the Chief Decision Officer.**

**Input**: 
- MiroFishSignal (Layer 1)
- DebateTranscript + BoardSynthesis (Layer 2)
- InstrumentPanel (Layer 3)
- Company policies + decision playbooks
- Organizational context (role, company, market, team)

**Output**: `ODEDecision` (formal decision contract)

```python
@dataclass
class ODEDecision:
    # Decision (accountable)
    decision: DecisionEnum  # ADVANCE, REJECT, FLAG, REINTERVIEW, RANK
    confidence: float       # 0-1, ODE's confidence
    
    # Drivers (why)
    decision_drivers: List[DecisionDriver]  # Culture, Role, Market, Retention, Team, Risk
    
    # Constraints (bounds)
    constraints_satisfied: bool
    constraint_list: List[str]
    
    # Uncertainty (honest)
    residual_uncertainty: float
    uncertainty_factors: List[str]
    
    # Action (next step)
    recommended_next_action: str
    
    # Accountability
    reasoning_summary: str
    decision_basis: str
    decision_id: str
    decision_timestamp: datetime
```

#### **ODE Sub-Components**

**1. Domain Models** (Encode organizational knowledge)
```
models/
├── culture_model.py        # Values, communication, leadership fit
├── role_model.py           # Competencies, experience, growth
├── market_model.py         # Role viability, comp trends, scarcity
├── retention_model.py      # 12/24mo outlook, flight risks
├── team_dynamics_model.py  # Manager fit, team chemistry
└── risk_model.py           # What can go wrong, impact, mitigation
```

**2. Policies Layer** (Encode company constraints)
```
policies/
├── company_policies.py     # Risk tolerance, culture strictness, diversity rules
├── decision_gates.py       # Must-pass thresholds (culture > 0.70, etc.)
└── constraints.py          # Hard limits (legal, compliance, authority)
```

**3. Playbooks Layer** (Encode decision workflows)
```
playbooks/
├── early_stage_playbook.py     # High risk, growth culture, flexible hiring
├── growth_stage_playbook.py    # Scaling, stability, execution-focused
├── mature_org_playbook.py      # Risk-averse, cultural fit critical
└── playbook_registry.py        # Select playbook based on company context
```

**4. Authority Boundaries** (Define ODE limits)
```
ODE CAN:
- Recommend hire/reject/flag/reinterview
- Rank candidates
- Demand more evidence
- Override agent consensus if policies justify
- Weight signals based on context

ODE CANNOT:
- Override legal/compliance constraints
- Ignore explicit company policies
- Make decisions outside defined scope
- Bypass required approval gates
```

**Implementation**: `orchestration/organizational_decision_engine.py`

**Status**: To be built (Phase 2, Weeks 4-5)

---

## Request Flow (Complete End-to-End)

### **Request In**
```python
result = await orchestrator.process(
    question="Should we hire Jane Doe for Senior PM?",
    domain="hr",
    candidate_data={...},
    company_context={...},
    market_snapshot={...}
)
```

### **Phase 1: MiroFish**
```
Orchestrator → MiroFish
  ├─ Run 1M agent simulation
  ├─ Return probability, confidence, diversity, convergence
  └─ Assess debate depth (minimal/light/full)
```

### **Phase 2: Agent Board Debate**
```
Orchestrator → Sub-swarms
  ├─ Culture Swarm: "Does Jane align with our values?"
  ├─ Skill Swarm: "Can Jane do this role and grow?"
  ├─ Retention Swarm: "Will Jane stay 18-24 months?"
  └─ [Each agent proposes, challenges, reconciles]
  
Optional escalations to MiroFish:
  └─ Agent: "Run scenario: Jane gets competing offer in 6mo"

Board synthesis:
  ├─ Representatives present findings
  ├─ Board debates trade-offs (culture vs. market, etc.)
  └─ Consensus reached (or minority opinions recorded)
```

### **Phase 3: Transcript + Instrument Panel**
```
TranscriptBuilder → Full debate record
  ├─ MiroFish assessment
  ├─ Each swarm's debate
  ├─ Board synthesis
  ├─ Confidence trajectory
  └─ Escalations logged

InstrumentPanel → Structured output
  ├─ Primary recommendation (ADVANCE TO FINAL ROUND)
  ├─ Simulation stack (0.79 baseline → 0.84 with debate)
  ├─ Reasoning layers (L1-L5)
  ├─ Factor map (Culture 0.88, Role 0.84, etc.)
  ├─ Swarm summaries (full text)
  ├─ Decision matrix (quantitative)
  └─ Risk surface (identified risks + mitigations)
```

### **Phase 4: ODE Decision**
```
ODE.evaluate()
  ├─ Read MiroFish signal: probability 0.79, confidence 0.72
  ├─ Read debate transcript: strong consensus, one retention flag
  ├─ Apply company policies:
  │   ├─ Culture strictness threshold: 0.70 ✓ (Jane: 0.88)
  │   ├─ Role gate: 0.75 ✓ (Jane: 0.84)
  │   ├─ Retention gate: 0.60 ✓ (Jane: 0.71)
  │   └─ Risk tolerance: moderate (can accept market volatility)
  ├─ Run culture model: 0.88 alignment
  ├─ Run role model: 0.84 fit
  ├─ Run market model: 0.72 viability (moderate volatility)
  ├─ Run retention model: 0.71 (18mo outlook)
  ├─ Run team dynamics model: 0.82 (manager fit excellent)
  ├─ Run risk model: low risk, retention mitigation needed
  ├─ Check playbook (Series B growth-stage):
  │   ├─ All gates pass? Yes
  │   ├─ Recommend action: ADVANCE TO FINAL ROUND
  │   └─ Next step: CEO + Head of Product final round
  └─ Produce ODEDecision:
      ├─ decision: ADVANCE_TO_FINAL_ROUND
      ├─ confidence: 0.81
      ├─ drivers: [Culture 0.88, Role 0.84, Team 0.82, Market 0.72, Retention 0.71]
      ├─ recommended_next_action: "Final round with CEO + Head of Product"
      └─ reasoning: "Jane demonstrates strong alignment across all gates..."
```

### **Response Out**
```
Customer sees ODE Decision + Instrument Panel:
├─ Primary recommendation (ADVANCE)
├─ Confidence (0.81)
├─ Drivers (ranked by impact)
├─ Constraints (all satisfied)
├─ Residual uncertainty (±0.08)
├─ Next action (final round details)
├─ Full reasoning chain (if they want to audit)
└─ Debate transcript (if they want full transparency)
```

---

## File Structure (Complete)

```
/Users/thikay/simoracle-backend/
├── reasoning/                          # Layer 1 + calibration (exists)
│   ├── api.py
│   ├── engine.py
│   └── pipeline.py
│
├── orchestration/                      # Layers 2, 3, 4 (TO BUILD)
│   ├── DESIGN.md                       # Phase 2 design (detailed)
│   ├── ORCHESTRATION_ARCHITECTURE.md   # This file
│   │
│   ├── Core Orchestration
│   │   ├── __init__.py
│   │   ├── message_bus.py              # Message routing + transcript
│   │   ├── orchestrator.py             # Entry point, agent registry
│   │   ├── agent_board.py              # Board coordination
│   │   └── debate_protocol.py          # Propose/challenge/reconcile
│   │
│   ├── HR Agents (Domain-specific)
│   │   ├── hr_agents/
│   │   │   ├── __init__.py
│   │   │   ├── culture_fit_agent.py
│   │   │   ├── team_dynamics_agent.py
│   │   │   ├── technical_depth_agent.py
│   │   │   ├── growth_potential_agent.py
│   │   │   ├── retention_risk_agent.py
│   │   │   ├── market_competitiveness_agent.py
│   │   │   └── swarm_config.py
│   │
│   ├── Organizational Decision Engine (Layer 4)
│   │   ├── organizational_decision_engine.py  # ODE core
│   │   ├── decision_contract.py              # ODEDecision schema
│   │   ├── models/
│   │   │   ├── culture_model.py
│   │   │   ├── role_model.py
│   │   │   ├── market_model.py
│   │   │   ├── retention_model.py
│   │   │   ├── team_dynamics_model.py
│   │   │   └── risk_model.py
│   │   ├── policies/
│   │   │   ├── company_policies.py
│   │   │   ├── decision_gates.py
│   │   │   └── constraints.py
│   │   ├── playbooks/
│   │   │   ├── early_stage_playbook.py
│   │   │   ├── growth_stage_playbook.py
│   │   │   ├── mature_org_playbook.py
│   │   │   └── playbook_registry.py
│   │
│   ├── Transcript Building
│   │   ├── transcript_builder.py
│   │   └── transcript_schema.py
│   │
│   └── Output Formatting (Layer 3 / Phase 3)
│       ├── output/
│       │   ├── instrument_panel.py
│       │   ├── formatting/
│       │   │   ├── panel_builder.py
│       │   │   ├── factor_map.py
│       │   │   ├── decision_matrix.py
│       │   │   └── confidence_trajectory.py
│       │   └── telemetry/
│       │       ├── version_stamp.py
│       │       ├── cycle_counter.py
│       │       └── metadata.py
│
└── tests/
    └── orchestration/
        ├── test_message_bus.py
        ├── test_debate_protocol.py
        ├── test_agent_board.py
        ├── test_ode.py
        ├── test_hr_agents.py
        └── test_end_to_end_hr.py
```

---

## Implementation Roadmap (5 Weeks)

### **Week 1: Core Infrastructure**
- [ ] Message bus (`message_bus.py`) — routing, subscription, transcript capture
- [ ] Orchestrator scaffold (`orchestrator.py`) — agent registry, initialization
- [ ] Basic agent interface — role definition, message contract
- [ ] MiroFish signal assessment — debate depth decision logic
- [ ] Unit tests for message bus

**Deliverable**: Message bus working, basic orchestrator spawning agents, signal assessment deciding debate depth

---

### **Week 2: Agent Board + Debate Protocol**
- [ ] Sub-swarm structure (`agent_board.py`)
- [ ] 6 HR agents (all files in `hr_agents/`)
- [ ] Debate protocol (`debate_protocol.py`) — propose/challenge/reconcile
- [ ] Escalation logic — agents request MiroFish simulations
- [ ] Representative election
- [ ] Board synthesis
- [ ] Integration tests for debate flow

**Deliverable**: Full debate cycle working for HR hiring scenario

---

### **Week 3: Transcript + Instrument Panel**
- [ ] Transcript builder (`transcript_builder.py`)
- [ ] Instrument panel formatter (`output/instrument_panel.py`)
- [ ] Factor map, decision matrix, confidence trajectory builders
- [ ] Version stamping, cycle counters, telemetry
- [ ] Full end-to-end HR test (MiroFish → debate → transcript → panel)
- [ ] Manual validation against 10 historical hiring decisions

**Deliverable**: Complete HR oracle with readable instrument panel output

---

### **Week 4: Organizational Decision Engine (Models)**
- [ ] Decision contract schema (`decision_contract.py`)
- [ ] Culture model (`models/culture_model.py`)
- [ ] Role model (`models/role_model.py`)
- [ ] Market model (`models/market_model.py`)
- [ ] Retention model (`models/retention_model.py`)
- [ ] Team dynamics model (`models/team_dynamics_model.py`)
- [ ] Risk model (`models/risk_model.py`)
- [ ] Unit tests for each model

**Deliverable**: All 6 models implemented and tested

---

### **Week 5: ODE (Policies + Playbooks + Integration)**
- [ ] Policy enforcement layer (`policies/company_policies.py`, `decision_gates.py`)
- [ ] Decision playbook registry (`playbooks/playbook_registry.py`)
- [ ] Early-stage, growth-stage, mature-org playbooks
- [ ] ODE core integration (`organizational_decision_engine.py`)
- [ ] Authority boundaries enforcement
- [ ] End-to-end integration test (all 4 layers)
- [ ] Production validation (10+ hiring scenarios)

**Deliverable**: Complete HR oracle ready for Omega tier customers

---

## Success Criteria

**Week 1**: ✅ Message bus, orchestrator, signal assessment  
**Week 2**: ✅ 6 agents debating, debate protocol working  
**Week 3**: ✅ Instrument panel readable and formatted correctly  
**Week 4**: ✅ All 6 ODE models implemented  
**Week 5**: ✅ End-to-end system working, 10 historical hires validated  

**Quality Gate**:
- Debate logic catches risks MiroFish alone misses
- Confidence trajectory makes sense (increases through debate)
- ODE decisions align with real hiring outcomes
- Instrument panels read like proprietary analytical software (not chatbot)
- All 4 layers integrated and tested

---

## Why This Is Billion-Dollar Ready

1. **It's not AI chatting** — it's a formal decision engine with accountability
2. **It's domain-agnostic** — same framework for M&A, real estate, compliance, operations
3. **It's policy-driven** — can encode any organization's risk tolerance, fairness rules, constraints
4. **It's transparent** — full debate visible, every decision has a contract
5. **It's enterprise-ready** — compliance, audit trails, approval gates built in
6. **It's defensible** — AI decisions backed by formal reasoning chain, not black box

**The moat is not the simulations (MiroFish does that).**  
**The moat is the transparent, policy-driven, accountable decision engine.**

That's what enterprises will pay for. That's what replaces entire departments.

---

## Next Step

Ready to build. Fork this architecture into implementation. Start Week 1.

Let me know when you want:
1. Detailed implementation specs for any component
2. Test cases / validation scenarios
3. Code scaffolding to start from
4. Integration plan with existing code

Or just say **"Go"** and I'll start writing Week 1 code.
