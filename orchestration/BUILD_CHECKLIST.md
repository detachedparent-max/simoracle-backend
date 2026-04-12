# SimOracle Phase 2 + 3 Build Checklist

**Timeline**: 5 weeks  
**Goal**: Complete HR oracle, ready to sell Omega tier  
**Status**: LOCKED IN, ready to execute  

---

## WEEK 1: Core Infrastructure

### Message Bus (`message_bus.py`)
- [ ] Message class (sender, receiver, type, content, timestamp, parent_id)
- [ ] MessageBus class with async send/broadcast/subscribe
- [ ] In-memory queue + transcript capture
- [ ] Message filtering by type/receiver
- [ ] Unit tests (message routing, subscription, transcript)

### Orchestrator Scaffold (`orchestrator.py`)
- [ ] Orchestrator class (entry point)
- [ ] Agent registry (track all spawned agents)
- [ ] Agent role dataclass (agent_id, domain, specialty, swarm_id, api_key, instructions)
- [ ] spawn_agents() method (initialize agents based on domain config)
- [ ] read_mirofish() method (call MiroFish, parse signal)
- [ ] assess_debate_depth() method (decide minimal/light/full)
- [ ] Unit tests (agent spawning, signal assessment)

### MiroFish Signal Assessment
- [ ] MiroFishSignal dataclass (probability, confidence, diversity, convergence, variance, drift)
- [ ] Debate depth logic:
  - confidence >= 0.85 AND diversity < 0.10 → "minimal"
  - confidence >= 0.70 → "light"
  - else → "full"
- [ ] Integration with existing MiroFish adapter
- [ ] Unit tests (signal parsing, debate depth logic)

### Basic Agent Interface
- [ ] AgentRole dataclass
- [ ] Agent message contract (what agents send/receive)
- [ ] Placeholder agent class (base class for all agents)
- [ ] Unit tests

**Deliverable**: Message bus working, orchestrator spawning agents, signal assessment deciding debate depth. Test with mock data.

---

## WEEK 2: Agent Board + Debate Protocol

### Agent Board (`agent_board.py`)
- [ ] AgentBoard class (orchestrates sub-swarms)
- [ ] SubSwarm class (groups agents by domain)
- [ ] swarm_internal_debate() method (agents within swarm argue)
- [ ] elect_representatives() method (each swarm picks one agent for board)
- [ ] board_synthesis_round() method (board debates cross-domain trade-offs)
- [ ] Unit tests (swarm creation, representative election, board debate)

### Debate Protocol (`debate_protocol.py`)
- [ ] propose() — Agent makes initial proposal
- [ ] challenge() — Other agents challenge proposal
- [ ] reconcile() — Agent responds to challenge, optional MiroFish escalation
- [ ] escalate_to_mirofish() — Agent requests additional simulation
- [ ] Unit tests (propose/challenge/reconcile flow, escalations)

### HR Agents (6 files in `hr_agents/`)

**Culture & Fit Swarm**:
- [ ] `culture_fit_agent.py` — Values alignment, communication style, leadership fit
  - System prompt, confidence rules, escalation triggers
- [ ] `team_dynamics_agent.py` — Manager fit, team chemistry, complementary strengths
  - System prompt, confidence rules, escalation triggers

**Skill & Trajectory Swarm**:
- [ ] `technical_depth_agent.py` — Required competencies, experience level, cognitive patterns
  - System prompt, confidence rules, escalation triggers
- [ ] `growth_potential_agent.py` — Growth trajectory, leadership potential, learning velocity
  - System prompt, confidence rules, escalation triggers

**Retention & Risk Swarm**:
- [ ] `retention_risk_agent.py` — Retention outlook, flight risk, stability
  - System prompt, confidence rules, escalation triggers
- [ ] `market_competitiveness_agent.py` — Compensation realism, market demand, skill scarcity
  - System prompt, confidence rules, escalation triggers

**Swarm Config**:
- [ ] `swarm_config.py` — HR domain swarm definitions (which agents in which swams)

**All agents need**:
- Agent initialization
- Message handling (receive messages, produce proposals/challenges/reconciliations)
- MiroFish escalation capability
- Confidence calibration
- Unit tests (one test per agent type)

### Integration Tests
- [ ] Full swarm debate cycle (propose → challenge → reconcile)
- [ ] Representative election
- [ ] Board debate
- [ ] Transcript capture (all messages logged)
- [ ] Test with mock HR hiring scenario

**Deliverable**: 6 agents debating, debate protocol working, all messages captured in transcript. Test with 2-3 hiring scenarios.

---

## WEEK 3: Transcript Builder + Instrument Panel

### Transcript Builder (`transcript_builder.py`)
- [ ] TranscriptBuilder class
- [ ] Transcript dataclass (phases, messages, confidence_trajectory, escalations)
- [ ] build_transcript() method (organize messages by phase)
- [ ] _build_confidence_trajectory() (track confidence L1→L2→L3→L4)
- [ ] _extract_escalations() (log all MiroFish escalations)
- [ ] Unit tests (transcript building, confidence trajectory, escalation extraction)

### Instrument Panel (`output/instrument_panel.py`)
- [ ] InstrumentPanelFormatter class
- [ ] format() method (takes transcript, MiroFish signal, final position → panel)
- [ ] Build sub-components:
  - [ ] `formatting/panel_builder.py` — Main panel structure
  - [ ] `formatting/factor_map.py` — Visual table of drivers
  - [ ] `formatting/decision_matrix.py` — Quantitative summary
  - [ ] `formatting/confidence_trajectory.py` — Confidence across phases
- [ ] Telemetry:
  - [ ] `telemetry/version_stamp.py` — "SimOracle v1.0"
  - [ ] `telemetry/cycle_counter.py` — Track debate cycles
  - [ ] `telemetry/metadata.py` — Timestamps, request IDs

### End-to-End Test
- [ ] Input: candidate data + role + company context
- [ ] Output: MiroFish → debate → transcript → instrument panel
- [ ] Validate:
  - Instrument panel reads like Bloomberg/proprietary software
  - No chatbot language ("I think," "seems like," etc.)
  - Structured data, clear formatting
  - All reasoning visible
- [ ] Test with 10 historical HR hiring decisions
- [ ] Compare panel recommendations against actual hiring outcomes

**Deliverable**: Complete HR oracle with readable instrument panel. 10 test cases passing. Panel looks professional, non-LLM.

---

## WEEK 4: ODE Models

### 6 Domain Models
- [ ] `models/culture_model.py`
  - evaluate_candidate() → alignment_score, red_flags, gaps
  - Methods: values alignment, communication fit, leadership compatibility, team compatibility

- [ ] `models/role_model.py`
  - evaluate_fit() → role_fit_score, gaps, stretch_areas
  - Methods: competencies check, experience level, cognitive patterns, growth trajectory

- [ ] `models/market_model.py`
  - evaluate_market_conditions() → market_viability, comp_realism, retention_risk, scarcity
  - Methods: role stability (next 12-24mo), compensation trends, skill scarcity, future role durability

- [ ] `models/retention_model.py`
  - evaluate_retention() → retention_12mo, retention_24mo, risk_factors, mitigations
  - Methods: flight risk assessment, competing offer likelihood, staying power

- [ ] `models/team_dynamics_model.py`
  - evaluate_team_fit() → team_fit_score, synergies, friction_risks, growth_enabled
  - Methods: manager compatibility, team chemistry, strength complementarity, multiplier effect

- [ ] `models/risk_model.py`
  - evaluate_risk() → risk_score, risk_factors, confidence_impact
  - Methods: identify risks, impact assessment, mitigation strategies

### Decision Contract (`decision_contract.py`)
- [ ] ODEDecision dataclass:
  - decision (enum)
  - confidence
  - decision_drivers (ranked list)
  - constraints_satisfied
  - residual_uncertainty
  - recommended_next_action
  - reasoning_summary
  - decision_id, timestamp

### Unit Tests
- [ ] Test each model with sample candidate data
- [ ] Verify outputs match expected ranges (0-1 scores)
- [ ] Test confidence calibration per model

**Deliverable**: All 6 models implemented, tested, producing structured outputs.

---

## WEEK 5: ODE Core + Policies + Playbooks + Integration

### Policies Layer
- [ ] `policies/company_policies.py`
  - CompanyPolicies dataclass:
    - false_positive_tolerance, false_negative_tolerance
    - culture_alignment_threshold, culture_override_allowed
    - off_profile_hiring_allowed, comp_ceiling_flexibility
    - non_traditional_background_bias, resume_gap_interpretation
  - Unit tests (policy reading, threshold checking)

- [ ] `policies/decision_gates.py`
  - Decision gates (culture > 0.70, role > 0.75, retention > 0.60)
  - gate_check() method (validate candidate against gates)
  - Unit tests

- [ ] `policies/constraints.py`
  - Hard constraints (legal, compliance, authority limits)
  - constraint_check() method
  - Unit tests

### Playbooks Layer
- [ ] `playbooks/early_stage_playbook.py`
  - Workflow for early-stage startups (high risk, growth culture, flexible)
  - execute() method

- [ ] `playbooks/growth_stage_playbook.py`
  - Workflow for growth-stage companies (scaling, stability, execution-focused)
  - execute() method

- [ ] `playbooks/mature_org_playbook.py`
  - Workflow for mature orgs (risk-averse, cultural fit critical, compliance-heavy)
  - execute() method

- [ ] `playbooks/playbook_registry.py`
  - select_playbook(company_context) → playbook
  - Unit tests (playbook selection based on context)

### ODE Core (`organizational_decision_engine.py`)
- [ ] OrganizationalDecisionEngine class
- [ ] evaluate() method:
  1. Read MiroFish signal, debate transcript, instrument panel
  2. Apply company policies + decision gates
  3. Run culture model, role model, market model, retention model, team model, risk model
  4. Select and execute appropriate playbook
  5. Resolve conflicts between models
  6. Produce ODEDecision

- [ ] Methods:
  - evaluate_against_gates()
  - run_models()
  - apply_playbook()
  - synthesize_decision()
  - produce_decision_contract()

### Authority Boundaries (`organizational_decision_engine.py`)
- [ ] Enforce authority limits (what ODE can/cannot do)
- [ ] Detect constraint violations
- [ ] Block decisions when legal/compliance limits hit
- [ ] Unit tests (authority enforcement)

### Full Integration Test
- [ ] Inputs: MiroFish signal, debate transcript, instrument panel, company policies, market context
- [ ] Process: MiroFish → agents debate → transcript → panel → ODE → decision
- [ ] Output: ODEDecision with reasoning
- [ ] Validate:
  - Decision aligns with policies
  - All gates checked
  - Drivers ranked correctly
  - Next action appropriate
  - Decision traces back to evidence

### Production Validation
- [ ] Test against 10-20 historical hiring decisions
- [ ] Compare ODE recommendations vs. actual outcomes
- [ ] Verify debate logic adds value (catches risks MiroFish misses)
- [ ] Verify confidence trajectory makes sense
- [ ] Document accuracy, insights, failure modes

**Deliverable**: Complete HR oracle end-to-end. All 4 layers working. ODE making decisions. Production validation passing.

---

## Testing Summary

| Layer | Component | Status |
|-------|-----------|--------|
| 1 | MiroFish | ✅ Exists (will integrate) |
| 2 | Message bus | 🔨 Week 1 |
| 2 | Orchestrator | 🔨 Week 1 |
| 2 | Agent board | 🔨 Week 2 |
| 2 | HR agents (6) | 🔨 Week 2 |
| 2 | Debate protocol | 🔨 Week 2 |
| 3 | Transcript builder | 🔨 Week 3 |
| 3 | Instrument panel | 🔨 Week 3 |
| 4 | ODE models (6) | 🔨 Week 4 |
| 4 | Policies + playbooks | 🔨 Week 5 |
| 4 | ODE core | 🔨 Week 5 |
| 📊 | End-to-end integration | 🔨 Week 5 |
| ✅ | Production validation | 🔨 Week 5 |

---

## Success Criteria (Checkpoints)

**Week 1 End**: ✅ Message bus working, orchestrator spawning agents, MiroFish signal assessment. Test with mock data.

**Week 2 End**: ✅ 6 agents debating, debate protocol working, transcript captured. Test with 2 hiring scenarios.

**Week 3 End**: ✅ Instrument panel readable, formatted correctly. 10 historical test cases validated.

**Week 4 End**: ✅ All 6 ODE models implemented, tested, producing structured outputs.

**Week 5 End**: ✅ ODE core working, policies + playbooks enforced, full end-to-end integration. 10-20 production test cases passing.

**Final Quality Gate**:
- Debate adds value (catches risks MiroFish alone misses) ✅
- Confidence trajectory makes sense ✅
- ODE decisions align with real outcomes ✅
- Instrument panel reads like pro software ✅
- All 4 layers integrated ✅

---

## Launch Readiness

When Week 5 complete:
- ✅ HR oracle fully functional
- ✅ Omega tier ready to sell
- ✅ Decision contracts in place
- ✅ Transparent reasoning chain visible to customers
- ✅ Ready to clone pattern to M&A, real estate, etc.

---

## Notes

- **No external dependencies added** — use existing code structure
- **Customer API key is shared context** — passed to orchestrator, used by all agents
- **MiroFish integration is async** — doesn't block debate
- **Transcript is first-class** — full record captured, not a side-effect
- **ODE is policy-driven** — encodes company's decision-making, not generic AI
- **Authority boundaries are hard limits** — can't be overridden

---

## When Week 5 Complete

You're ready to:
1. **Clone pattern to M&A domain** (2 weeks)
2. **Clone pattern to real estate** (2 weeks)
3. **Build white-label dashboard** (1-2 weeks)
4. **Launch Omega tier** (2 weeks + sales)
5. **Scale to $1B** (18-24 months)

**Go.**
