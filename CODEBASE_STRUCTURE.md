# SimOracle Codebase Structure (Current Build)

## 🎯 Current Phase: Building Phase 2 + 3 (Orchestration Layer + Output Formatting)

**Status**: Week 1 implementation starting  
**Focus**: Agent orchestration framework, organizational decision engine, instrument panel output  
**Timeline**: 5 weeks  

---

## Directory Structure (CLEAN)

```
/Users/thikay/simoracle-backend/
│
├── 📋 DOCUMENTATION (Read these)
│   ├── CODEBASE_STRUCTURE.md              ← You are here
│   ├── PHASE2_PHASE3_EXECUTIVE.md         ← High-level overview
│   ├── README.md                          ← Original project README
│   └── orchestration/
│       ├── ORCHESTRATION_ARCHITECTURE.md  ← Master blueprint
│       ├── DESIGN.md                      ← Phase 2 detailed spec
│       └── BUILD_CHECKLIST.md             ← Week-by-week tasks
│
├── 🧠 REASONING (Existing - DO NOT MODIFY)
│   ├── api.py                             ← Public API (UniversalPredictionEngine)
│   ├── engine.py                          ← Core reasoning engine
│   ├── pipeline.py                        ← MiroFish integration pipeline
│   ├── schemas.py                         ← Data schemas
│   ├── blender.py                         ← Signal blending
│   ├── layers/                            ← 6 reasoning layers (production)
│   │   ├── behavioral_bias.py
│   │   ├── temporal.py
│   │   ├── confidence_cal.py
│   │   ├── validation.py
│   │   └── __init__.py
│   ├── monitoring/                        ← Drift detection, calibration
│   │   ├── drift_tuning.py
│   │   └── calibration.py
│   ├── _internal/                         ← MiroFish hidden here (customer doesn't see)
│   │   ├── oracles/
│   │   │   ├── interface.py               ← OracleProvider interface
│   │   │   ├── mirofish.py                ← MiroFish adapter
│   │   │   └── mirofish_client.py         ← HTTP client
│   │   ├── layers/
│   │   └── monitoring/
│   └── __init__.py
│
├── 🤖 ORCHESTRATION (Building - PHASE 2 + 3)
│   ├── __init__.py
│   ├── ORCHESTRATION_ARCHITECTURE.md      ← Start here
│   │
│   ├── Week 1: Core Infrastructure
│   │   ├── message_bus.py                 ← TO BUILD
│   │   ├── orchestrator.py                ← TO BUILD
│   │   └── [tests]
│   │
│   ├── Week 2: Agent Board + HR Agents
│   │   ├── agent_board.py                 ← TO BUILD
│   │   ├── debate_protocol.py             ← TO BUILD
│   │   ├── hr_agents/                     ← TO BUILD
│   │   │   ├── culture_fit_agent.py
│   │   │   ├── team_dynamics_agent.py
│   │   │   ├── technical_depth_agent.py
│   │   │   ├── growth_potential_agent.py
│   │   │   ├── retention_risk_agent.py
│   │   │   ├── market_competitiveness_agent.py
│   │   │   └── swarm_config.py
│   │   └── [tests]
│   │
│   ├── Week 3: Transcript + Output
│   │   ├── transcript_builder.py          ← TO BUILD
│   │   ├── output/                        ← TO BUILD
│   │   │   ├── instrument_panel.py
│   │   │   ├── formatting/
│   │   │   │   ├── panel_builder.py
│   │   │   │   ├── factor_map.py
│   │   │   │   ├── decision_matrix.py
│   │   │   │   └── confidence_trajectory.py
│   │   │   └── telemetry/
│   │   │       ├── version_stamp.py
│   │   │       ├── cycle_counter.py
│   │   │       └── metadata.py
│   │   └── [tests]
│   │
│   ├── Week 4: ODE Models
│   │   ├── organizational_decision_engine.py  ← TO BUILD
│   │   ├── decision_contract.py              ← TO BUILD
│   │   ├── models/                           ← TO BUILD
│   │   │   ├── culture_model.py
│   │   │   ├── role_model.py
│   │   │   ├── market_model.py
│   │   │   ├── retention_model.py
│   │   │   ├── team_dynamics_model.py
│   │   │   └── risk_model.py
│   │   └── [tests]
│   │
│   └── Week 5: ODE Core + Policies + Playbooks
│       ├── policies/                      ← TO BUILD
│       │   ├── company_policies.py
│       │   ├── decision_gates.py
│       │   └── constraints.py
│       ├── playbooks/                     ← TO BUILD
│       │   ├── early_stage_playbook.py
│       │   ├── growth_stage_playbook.py
│       │   ├── mature_org_playbook.py
│       │   └── playbook_registry.py
│       └── [tests]
│
├── 🗄️ DATABASE (Existing - DO NOT TOUCH)
│   ├── schema.py
│   ├── queries.py
│   └── __init__.py
│
├── 📊 ANALYTICS (Existing - DO NOT TOUCH)
│   ├── (Kalshi trading bot analytics - archive candidate)
│   └── ...
│
├── 📡 MARKET FEEDS (Existing - DO NOT TOUCH)
│   ├── kalshi.py
│   └── (v2.5 trading bot code - archive candidate)
│
├── 🔧 API (Existing - DO NOT TOUCH)
│   ├── (FastAPI routes - v2.5 trading bot)
│   └── ...
│
├── 🌐 APP / SERVER (Existing - DO NOT TOUCH)
│   ├── app.py, server.js
│   ├── (Frontend/backend glue from v2.5)
│   └── ...
│
├── 📚 DOCS (Reference)
│   └── (Old API docs, architecture, etc.)
│
└── 🔒 ARCHIVE (Old versions - can delete)
    ├── [TBD - move obsolete files here]
    └── (Keep as backup reference only)
```

---

## What's What (Quick Reference)

### ✅ Foundation Layers (STABLE - DON'T TOUCH)

**`reasoning/`** — The universal prediction engine (6 reasoning layers)
- Calibrates MiroFish output
- Applies bias detection, temporal adjustment, confidence calibration
- Production-ready, tested, works for any domain
- **Status**: Complete, locked
- **Use**: Import from `reasoning.api.UniversalPredictionEngine`

**`database/`, `api/`, `app/`** — FastAPI backend (v2.5 trading bot)
- Legacy code from Kalshi trading phase
- Not needed for Phase 2/3
- Will archive to separate folder (see below)

### 🚀 Building Now (ACTIVE - BUILDING)

**`orchestration/`** — The new orchestration framework
- Message bus (agent routing + transcript)
- Orchestrator (entry point, agent registry)
- Agent board (hierarchical debate)
- 6 HR agents (domain-specific debate)
- Transcript builder
- Instrument panel formatter
- ODE (organizational decision engine)
- **Status**: Starting Week 1, not yet built
- **Structure**: See BUILD_CHECKLIST.md for week-by-week tasks

---

## What's Being Built This Week

### Week 1: Foundation
```
orchestration/
├── message_bus.py            ← Message routing + transcript capture
├── orchestrator.py           ← Entry point, agent registry, MiroFish integration
├── __init__.py               ← Public API
└── tests/
    ├── test_message_bus.py
    └── test_orchestrator.py
```

**Goals**:
- Message bus working (send, broadcast, subscribe, transcript)
- Orchestrator spawning agents
- MiroFish signal assessment (decide debate depth)
- Unit tests passing

---

## How to Navigate This Code

### If you want to understand the current phase:
1. Read: `PHASE2_PHASE3_EXECUTIVE.md` (10 min overview)
2. Read: `orchestration/ORCHESTRATION_ARCHITECTURE.md` (30 min blueprint)
3. Read: `orchestration/BUILD_CHECKLIST.md` (2 min week-by-week)

### If you want to build Phase 2 (Week 1-3):
1. Start with: `orchestration/DESIGN.md`
2. Follow: `orchestration/BUILD_CHECKLIST.md` weeks 1-3
3. Implement: `orchestration/message_bus.py` and `orchestration/orchestrator.py`

### If you want to build Phase 3 (Week 4-5):
1. Start with: `orchestration/BUILD_CHECKLIST.md` weeks 4-5
2. Implement: ODE models, policies, playbooks, ODE core

### If you want to understand the foundation:
1. Read: `reasoning/api.py` (public API)
2. Read: `reasoning/engine.py` (core reasoning)
3. Note: MiroFish is hidden in `reasoning/_internal/oracles/`

---

## Files to Ignore (Legacy v2.5 Kalshi Trading Bot)

**These are old and should be archived** (to archive folder):

- `analytics/` — Trading analytics (v2.5)
- `market_feeds/kalshi.py` — Kalshi feed integration (v2.5)
- `api/` — FastAPI routes for trading (v2.5)
- `app/`, `app.py`, `server.js` — Frontend/backend glue (v2.5)
- `API_BUILD_COMPLETION_REPORT.md` — Trading bot docs
- `API_DOCUMENTATION.md` — Trading bot API
- `ARCHITECTURE.md` — Trading bot architecture
- `BUILD_SUMMARY.md` — Trading bot build
- `DEPLOYMENT.md` — Trading bot deployment
- `FRONTEND_INTEGRATION.md` — Trading bot frontend
- `INTEGRATION_BUILD_SUMMARY.md` — Trading bot integration
- `LAUNCH_CHECKLIST.md` — Trading bot launch
- `QA_REPORT.md` — Trading bot QA

**Why**: SimOracle v2.5 was a Kalshi prediction trading bot. Phase 2/3 is building the enterprise HR oracle (completely different product). These files are confusing.

---

## Archive Plan

When you're ready, run:
```bash
mkdir -p /Users/thikay/simoracle-backend/_archive_v2.5_kalshi_trading_bot
mv analytics/ market_feeds/kalshi.py api/ app/ app.py server.js _archive_v2.5_kalshi_trading_bot/
mv API_BUILD_COMPLETION_REPORT.md API_DOCUMENTATION.md ARCHITECTURE.md BUILD_SUMMARY.md DEPLOYMENT.md _archive_v2.5_kalshi_trading_bot/
mv FRONTEND_INTEGRATION.md INTEGRATION_BUILD_SUMMARY.md LAUNCH_CHECKLIST.md QA_REPORT.md _archive_v2.5_kalshi_trading_bot/
```

**After archiving**, the codebase becomes clean:
- `reasoning/` — Prediction engine (keep)
- `orchestration/` — Phase 2/3 build (focus here)
- `database/` — Data layer (keep, might use)
- Documentation and READMEs (keep for reference)

---

## Summary

**Current Build**:
- Layer 1 (MiroFish): ✅ Exists, wrapped in `reasoning/`
- Layer 2 (Agent Board): 🔨 Building (Week 1-2)
- Layer 3 (Instrument Panel): 🔨 Building (Week 3)
- Layer 4 (ODE): 🔨 Building (Week 4-5)

**What's clear now**:
- Legacy v2.5 trading bot code is archived
- Phase 2/3 work is in `orchestration/`
- Foundation (`reasoning/`) is stable and unchanged
- Clear week-by-week path in BUILD_CHECKLIST.md

**Ready to build**: Week 1 starts now.

---

## Files You Should Read (In Order)

1. **This file** — You're reading it (context)
2. `PHASE2_PHASE3_EXECUTIVE.md` — High-level overview (10 min)
3. `orchestration/ORCHESTRATION_ARCHITECTURE.md` — Complete blueprint (30 min)
4. `orchestration/BUILD_CHECKLIST.md` — Week 1 tasks (reference)
5. `orchestration/DESIGN.md` — Detailed Phase 2 spec (reference)

**Then start building** Week 1 code.
