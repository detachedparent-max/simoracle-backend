---
name: Unified Prediction Engine - Complete Abstraction Design
description: Hide MiroFish implementation behind clean OracleProvider interface. Customers only see UniversalPredictionEngine.
type: spec
---

# Unified Prediction Engine: Complete Abstraction Design

## Goal

Customers deploy **one clean product** (`UniversalPredictionEngine`) without knowing or caring about MiroFish. The reasoning layer, not the simulation engine, is the differentiation.

---

## Architecture

### Public API (What Customers Use)

```python
# simoracle/__init__.py
from .engine import UniversalPredictionEngine
from .schemas import ReasoningOutput, PredictionConfig
from .oracles import OracleProvider  # Optional for advanced users

__all__ = [
    "UniversalPredictionEngine",
    "ReasoningOutput",
    "PredictionConfig",
    "OracleProvider",  # Only for bring-your-own-oracle use case
]
```

**Customers never import:**
- `MiroFishStreamingClient`
- `MiroFishOracle`
- `PartialMiroFishResult`
- Anything from `_internal/`

### Directory Structure

```
simoracle-backend/
├── reasoning/
│   ├── __init__.py                 # Re-exports public API
│   ├── engine.py                   # UniversalPredictionEngine (PUBLIC)
│   ├── schemas.py                  # ReasoningOutput, etc. (PUBLIC)
│   ├── config.py                   # PredictionConfig (PUBLIC)
│   │
│   ├── _internal/                  # Hidden implementation
│   │   ├── __init__.py
│   │   │
│   │   ├── oracles/                # Oracle implementations (hidden)
│   │   │   ├── __init__.py
│   │   │   ├── interface.py        # OracleProvider abstract class
│   │   │   ├── mirofish.py         # MiroFishOracle (implementation detail)
│   │   │   └── mirofish_client.py  # MiroFishStreamingClient, subprocess mgmt
│   │   │
│   │   ├── layers/                 # Reasoning layers (moved here)
│   │   │   ├── behavioral_bias.py
│   │   │   ├── temporal.py
│   │   │   ├── confidence_cal.py
│   │   │   └── validation.py
│   │   │
│   │   └── monitoring/             # Monitoring (moved here)
│   │       ├── calibration.py
│   │       └── drift_tuning.py
│   │
│   ├── layers/                     # Keep for backward compat (import from _internal)
│   │   ├── __init__.py
│   │   ├── behavioral_bias.py      # from .._internal.layers import *
│   │   └── ...
│   │
│   └── monitoring/                 # Keep for backward compat
│       └── __init__.py
```

---

## Core Classes

### 1. `OracleProvider` Interface (Hidden)

**File:** `reasoning/_internal/oracles/interface.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class OracleResult:
    """Standard output from any oracle"""
    probability: float           # 0-1
    narrative: str              # Explanation
    supporting_data: Dict[str, Any]  # Oracle-specific details
    metadata: Dict[str, Any]    # Trace logs, agent counts, etc.

class OracleProvider(ABC):
    """
    Abstract oracle provider.
    
    Any system that produces a probability distribution
    can be plugged in here (MiroFish, LLM, statistical model, etc.)
    """
    
    @abstractmethod
    async def get_probability(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None
    ) -> OracleResult:
        """
        Generate a probability for a question.
        
        Args:
            question: The prediction question
            domain: Domain type (weather, hr, mna, geopolitics, etc.)
            context: Additional context (data_age_days, expert_opinion, etc.)
        
        Returns:
            OracleResult with probability, narrative, and metadata
        """
        pass
    
    async def stream_probabilities(self, question: str, domain: str, context: Optional[Dict] = None):
        """
        Optional: Stream partial probabilities as they're computed.
        Yields OracleResult objects incrementally.
        Default: yields single final result.
        """
        yield await self.get_probability(question, domain, context)
```

### 2. `MiroFishOracle` Implementation (Hidden)

**File:** `reasoning/_internal/oracles/mirofish.py`

```python
from .interface import OracleProvider, OracleResult
from .mirofish_client import MiroFishStreamingClient, PipelineConfig
from typing import Dict, Any, Optional, AsyncIterator

class MiroFishOracle(OracleProvider):
    """
    MiroFish-backed oracle provider.
    
    Implementation detail. Customers don't see this.
    Uses 1M agent simulations to generate probability distributions.
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Args:
            config: PipelineConfig for MiroFish simulation
                   (seed, num_agents, stream_interval, etc.)
        """
        self.client = MiroFishStreamingClient(config or PipelineConfig())
    
    async def get_probability(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None
    ) -> OracleResult:
        """
        Run full MiroFish simulation, return final probability.
        """
        # Consume all streamed results, use final
        final_result = None
        async for result in self.stream_probabilities(question, domain, context):
            final_result = result
        
        return final_result
    
    async def stream_probabilities(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[OracleResult]:
        """
        Stream partial probabilities as MiroFish simulation progresses.
        
        Yields OracleResult for each partial checkpoint.
        """
        async for partial in self.client.run_simulation(
            question=question,
            domain=domain,
            context=context
        ):
            yield OracleResult(
                probability=partial.probability,
                narrative=partial.narrative,
                supporting_data={
                    "agents_run": partial.agents_run,
                    "rounds_completed": partial.rounds_completed,
                    "is_partial": True,
                },
                metadata={"trace": partial.trace}
            )
```

### 3. `UniversalPredictionEngine` (Public)

**File:** `reasoning/engine.py`

```python
from typing import Optional, Dict, Any
from ._internal.oracles.interface import OracleProvider
from ._internal.oracles.mirofish import MiroFishOracle
from ._internal.layers import (
    BehavioralBiasDetector,
    TemporalAdjuster,
    ConfidenceCalibrator,
    InputValidator,
)
from ._internal.monitoring import CalibrationMonitor, DriftDetector, AdaptiveTuner
from .schemas import ReasoningOutput, ReasoningRequest

class UniversalPredictionEngine:
    """
    Production-ready prediction engine.
    
    Combines multi-agent simulations with domain-agnostic reasoning
    to produce calibrated predictions at 85%+ confidence.
    
    Usage:
        engine = UniversalPredictionEngine()
        result = await engine.predict(
            question="Will X happen?",
            domain="weather",
            customer_data={...}
        )
    """
    
    def __init__(
        self,
        oracle_provider: Optional[OracleProvider] = None,
        learning_rate: float = 0.1,
    ):
        """
        Args:
            oracle_provider: Probability source (defaults to MiroFish)
                           Can be any OracleProvider implementation
            learning_rate: Adaptive tuning learning rate
        """
        # Use MiroFish by default; customer can inject their own oracle
        self.oracle = oracle_provider or MiroFishOracle()
        
        # Reasoning layers
        self.bias_detector = BehavioralBiasDetector()
        self.temporal_adjuster = TemporalAdjuster()
        self.confidence_calibrator = ConfidenceCalibrator()
        self.validator = InputValidator()
        self.blender = ProbabilityBlender()
        
        # Monitoring
        self.calibration_monitor = CalibrationMonitor()
        self.drift_detector = DriftDetector()
        self.adaptive_tuner = AdaptiveTuner(learning_rate)
    
    async def predict(
        self,
        question: str,
        domain: str,
        customer_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningOutput:
        """
        Generate a calibrated prediction.
        
        Args:
            question: The prediction question
            domain: Domain (weather, hr, mna, geopolitics, etc.)
            customer_data: Customer-provided context
            context: Additional system context (data_age_days, etc.)
        
        Returns:
            ReasoningOutput with calibrated probability, confidence, reasoning chain
        """
        # 1. Validation
        validation = self.validator.validate(customer_data, context or {})
        if not validation.passed:
            return ReasoningOutput(
                validation_level="fail",
                error_message=validation.error,
                caveats=validation.warnings
            )
        
        # 2. Get probability from oracle
        oracle_result = await self.oracle.get_probability(
            question=question,
            domain=domain,
            context=context
        )
        
        base_probability = oracle_result.probability
        
        # 3. Apply reasoning layers
        bias_signals = self.bias_detector.detect(customer_data, base_probability)
        temporal_signals = self.temporal_adjuster.adjust(context or {})
        
        # 4. Calibrate confidence
        confidence = self.confidence_calibrator.calibrate(
            base_probability=base_probability,
            bias_signals=bias_signals,
            temporal_signals=temporal_signals,
            customer_data=customer_data,
            context=context or {}
        )
        
        # 5. Blend adjustments
        calibrated_probability = self.blender.blend(
            base_probability=base_probability,
            bias_adjustment=sum(s.adjustment for s in bias_signals),
            temporal_adjustment=sum(s.adjustment for s in temporal_signals),
        )
        
        # 6. Build reasoning chain
        reasoning_chain = [
            {"layer": "Oracle", "adjustment": 0, "explanation": oracle_result.narrative},
            {"layer": "Behavioral Bias", "adjustment": sum(s.adjustment for s in bias_signals), "signals": bias_signals},
            {"layer": "Temporal", "adjustment": sum(s.adjustment for s in temporal_signals), "signals": temporal_signals},
            {"layer": "Confidence Calibration", "confidence": confidence.value},
        ]
        
        # 7. Build output
        result = ReasoningOutput(
            base_probability=base_probability,
            calibrated_probability=calibrated_probability,
            confidence_level=confidence.level,
            confidence=confidence.value,
            recommendation=self._make_recommendation(calibrated_probability, confidence),
            reasoning_chain=reasoning_chain,
            caveats=validation.warnings,
            validation_level="pass",
        )
        
        # 8. Monitor (for feedback loops)
        self.calibration_monitor.record(confidence.value, None)  # Outcome added later via record_outcome()
        
        return result
    
    def record_outcome(
        self,
        prediction_id: str,
        confidence: float,
        was_correct: bool,
        bias_signals: Optional[list] = None,
        staleness_days: int = 0,
    ):
        """
        Record actual outcome for monitoring and tuning.
        
        Used to:
        - Monitor drift (is accuracy dropping?)
        - Tune bias weights (which signals are reliable?)
        - Calibrate confidence levels (do high-confidence predictions actually hit high accuracy?)
        """
        self.drift_detector.record(prediction_id, confidence, was_correct)
        self.adaptive_tuner.record_outcome(
            confidence=confidence,
            bias_signals=bias_signals or [],
            staleness_days=staleness_days,
            was_correct=was_correct,
        )
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check engine health: drift, calibration, tuning status.
        """
        return {
            "drift": self.drift_detector.check_drift().to_dict(),
            "calibration": self.calibration_monitor.get_stats(),
            "tuned_parameters": self.adaptive_tuner.get_tuned_parameters(),
        }
    
    @staticmethod
    def _make_recommendation(probability: float, confidence):
        """Generate human-readable recommendation."""
        if probability >= 0.7 and confidence.value >= 0.75:
            return "✅ YES (High confidence)"
        elif probability >= 0.6:
            return "👍 LEAN YES (Cautious)"
        elif probability >= 0.5:
            return "🤔 UNCERTAIN"
        elif probability >= 0.3:
            return "👎 LEAN NO (Cautious)"
        else:
            return "❌ NO (High confidence)"
```

### 4. Public Schemas

**File:** `reasoning/schemas.py`

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class ConfidenceLevel(str, Enum):
    """Confidence categories"""
    HIGH = "high"
    MODERATE = "moderate"
    GUARDED = "guarded"
    LOW = "low"

@dataclass
class ReasoningOutput:
    """Standard output from prediction engine"""
    base_probability: float
    calibrated_probability: float
    confidence: float                    # 0-1
    confidence_level: ConfidenceLevel
    recommendation: str
    reasoning_chain: List[Dict[str, Any]]
    caveats: List[str] = field(default_factory=list)
    validation_level: str = "pass"       # pass, warn, fail
    error_message: Optional[str] = None
    staleness_ceiling: Optional[float] = None

@dataclass
class PredictionConfig:
    """Configuration for UniversalPredictionEngine"""
    base_agents: int = 1_000_000
    determinism_seed: Optional[int] = None
    stream_interval_seconds: float = 5.0
    enable_early_exit: bool = False
    min_confidence_for_early_exit: float = 0.85
```

### 5. Public Exports (Backward Compat)

**File:** `reasoning/__init__.py`

```python
# Public API
from .engine import UniversalPredictionEngine
from .schemas import ReasoningOutput, ConfidenceLevel, PredictionConfig
from ._internal.oracles.interface import OracleProvider

# For advanced users (optional)
from ._internal.oracles.mirofish import MiroFishOracle

# Backward compat: re-export old imports
# (customers using old code still work)
from ._internal.layers import (
    BehavioralBiasDetector,
    TemporalAdjuster,
    ConfidenceCalibrator,
    InputValidator,
)
from ._internal.monitoring import (
    CalibrationMonitor,
    DriftDetector,
    AdaptiveTuner,
    PredictionHealthMonitor,
)

__all__ = [
    "UniversalPredictionEngine",
    "ReasoningOutput",
    "ConfidenceLevel",
    "PredictionConfig",
    "OracleProvider",
    # Backward compat
    "BehavioralBiasDetector",
    "TemporalAdjuster",
    "ConfidenceCalibrator",
    "InputValidator",
    "CalibrationMonitor",
    "DriftDetector",
    "AdaptiveTuner",
    "PredictionHealthMonitor",
]
```

---

## Usage Examples

### Standard (Customers Use This)

```python
from simoracle import UniversalPredictionEngine

# Create engine (uses MiroFish by default, but hidden)
engine = UniversalPredictionEngine()

# Make prediction
result = await engine.predict(
    question="Will the temperature exceed 90°F in Austin tomorrow?",
    domain="weather",
    customer_data={
        "city": "Austin",
        "forecast_high": 88,
        "historical_high": 94,
        "trend": "warming"
    },
    context={"data_age_days": 0}
)

print(f"Probability: {result.calibrated_probability:.0%}")
print(f"Confidence: {result.confidence_level.value}")
print(f"Recommendation: {result.recommendation}")

# Record outcome (for monitoring)
engine.record_outcome(
    prediction_id="pred_123",
    confidence=result.confidence,
    was_correct=True,
    staleness_days=1
)

# Check health
health = engine.check_health()
```

### Advanced (Bring Your Own Oracle)

```python
from simoracle import UniversalPredictionEngine, OracleProvider

class CustomerOracle(OracleProvider):
    async def get_probability(self, question, domain, context):
        # Customer's proprietary model
        return {"probability": 0.75, "narrative": "..."}

engine = UniversalPredictionEngine(oracle_provider=CustomerOracle())
result = await engine.predict(...)
```

---

## Migration Plan

### Phase 1: Refactor (Today)
1. Create `_internal/` directory structure
2. Move existing code (layers, monitoring) to `_internal/`
3. Create `OracleProvider` interface
4. Create `MiroFishOracle` wrapper (hides `MiroFishStreamingClient`)
5. Update `UniversalPredictionEngine` to use oracle abstraction
6. Keep old imports working (backward compat re-exports)

### Phase 2: Test (Today)
1. Test `UniversalPredictionEngine` with mock and real MiroFish
2. Verify Iran scenario works end-to-end
3. Verify customer code never sees "MiroFish" in class names

### Phase 3: Document (Tomorrow)
1. Update README with usage examples
2. Create deployment guide for customers
3. Document OracleProvider interface for advanced users

---

## Backward Compatibility

Existing code still works:

```python
# Old way (still works)
from reasoning.layers import BehavioralBiasDetector
from reasoning.monitoring import DriftDetector

# New way (preferred)
from simoracle import UniversalPredictionEngine
```

---

## Success Criteria

- ✅ Customers only import `UniversalPredictionEngine`
- ✅ No mention of "MiroFish" in customer-facing code
- ✅ MiroFish details are in `_internal/`
- ✅ Customers can bring their own oracle (optional advanced feature)
- ✅ Iran scenario test passes with 85%+ confidence
- ✅ Backward compat: old imports still work
