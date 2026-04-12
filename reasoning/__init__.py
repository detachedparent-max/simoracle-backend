"""
Simoracle - Universal Prediction Engine

Production-ready prediction engine combining 1M agent simulations
with domain-agnostic reasoning to produce calibrated predictions.

Clean Public API:
    from simoracle import UniversalPredictionEngine, OracleProvider

    # Standard (uses MiroFish by default)
    engine = UniversalPredictionEngine()
    result = await engine.predict(
        question="Will X happen?",
        domain="weather",
        customer_data={...}
    )

    # Advanced (bring your own oracle)
    class MyOracle(OracleProvider):
        async def get_probability(self, question, domain, context):
            return OracleResult(probability=0.75, narrative="...")

    engine = UniversalPredictionEngine(oracle_provider=MyOracle())

Backward Compatibility:
    # Old imports still work
    from reasoning.pipeline import PredictionPipeline
    from reasoning.layers import BehavioralBiasDetector
"""

# Public API - customers import from here
from .api import UniversalPredictionEngine
from ._internal.oracles.interface import OracleProvider
from ._internal.oracles.mirofish_client import PipelineConfig as PredictionConfig
from .schemas import (
    ReasoningOutput,
    ConfidenceLevel,
)

# Backward compatibility - old imports still work
from .pipeline import (
    PredictionPipeline,
    MockPredictionPipeline,
    PipelineConfig,
    MiroFishStreamingClient,
    PartialMiroFishResult,
    FullMiroFishResult,
    EarlySignal,
)
from .layers import (
    BehavioralBiasDetector,
    TemporalAdjuster,
    ConfidenceCalibrator,
    InputValidator,
)
from .monitoring import (
    CalibrationMonitor,
    DriftDetector,
    AdaptiveTuner,
    PredictionHealthMonitor,
)

__all__ = [
    # Public API (customers use these)
    "UniversalPredictionEngine",
    "OracleProvider",
    "ReasoningOutput",
    "ConfidenceLevel",
    "PredictionConfig",
    # Backward compat
    "PredictionPipeline",
    "MockPredictionPipeline",
    "PipelineConfig",
    "MiroFishStreamingClient",
    "PartialMiroFishResult",
    "FullMiroFishResult",
    "EarlySignal",
    "BehavioralBiasDetector",
    "TemporalAdjuster",
    "ConfidenceCalibrator",
    "InputValidator",
    "CalibrationMonitor",
    "DriftDetector",
    "AdaptiveTuner",
    "PredictionHealthMonitor",
]
