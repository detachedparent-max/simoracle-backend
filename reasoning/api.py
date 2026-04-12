"""
Public API for Simoracle Universal Prediction Engine

Customers import from here. All MiroFish/implementation details are hidden.

Usage:
    from simoracle import UniversalPredictionEngine

    engine = UniversalPredictionEngine()
    result = await engine.predict(
        question="Will X happen?",
        domain="weather",
        customer_data={...}
    )
"""

import logging
from typing import Optional, Dict, Any
from .engine import UniversalPredictionEngine as _EngineCore
from ._internal.oracles.mirofish import MiroFishOracle
from ._internal.oracles.interface import OracleProvider
from .schemas import ReasoningOutput

logger = logging.getLogger(__name__)


class UniversalPredictionEngine:
    """
    Production-ready prediction engine.

    Combines multi-agent simulations with domain-agnostic reasoning
    to produce calibrated predictions at 85%+ confidence.

    Customers use this. Implementation details (MiroFish, etc.) are hidden.

    Usage:
        engine = UniversalPredictionEngine()
        result = await engine.predict(
            question="Will the temperature exceed 90°F in Austin tomorrow?",
            domain="weather",
            customer_data={"forecast_high": 88, "historical_high": 94}
        )

        print(f"Probability: {result.calibrated_probability:.0%}")
        print(f"Confidence: {result.confidence_level.value}")
        print(f"Recommendation: {result.recommendation}")
    """

    def __init__(
        self,
        oracle_provider: Optional[OracleProvider] = None,
        learning_rate: float = 0.1,
    ):
        """
        Initialize the prediction engine.

        Args:
            oracle_provider: Probability source
                By default, uses MiroFish (1M agent simulations)
                Advanced users can provide their own OracleProvider
            learning_rate: Adaptive tuning learning rate (0.0-1.0)
        """
        # Use MiroFish by default; customer can inject their own
        self.oracle = oracle_provider or MiroFishOracle()
        self._core_engine = _EngineCore()

        logger.info(
            f"UniversalPredictionEngine initialized "
            f"(oracle: {type(self.oracle).__name__}, learning_rate: {learning_rate})"
        )

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
                Example: "Will the temperature exceed 90°F in Austin tomorrow?"
            domain: Domain type
                Options: "weather", "hr", "mna", "geopolitics", "law", "real_estate"
            customer_data: Customer-provided context
                Example: {"forecast_high": 88, "historical_high": 94, "trend": "warming"}
            context: Optional system context
                Example: {"data_age_days": 0, "expert_opinion": 0.7}

        Returns:
            ReasoningOutput with:
            - calibrated_probability: Final prediction (0-1)
            - confidence: How confident we are (0-1)
            - confidence_level: HIGH, MODERATE, GUARDED, LOW
            - recommendation: Actionable advice
            - reasoning_chain: How we arrived at the prediction
            - caveats: Important limitations
        """
        context = context or {}

        # Get probability from oracle (MiroFish by default)
        try:
            oracle_result = await self.oracle.get_probability(
                question=question, domain=domain, context=context
            )
        except Exception as e:
            logger.error(f"Oracle failed: {e}")
            raise RuntimeError(f"Probability generation failed: {e}") from e

        # Feed oracle output to core reasoning engine
        mirofish_output = {
            "probability": oracle_result.probability,
            "narrative": oracle_result.narrative,
            "metadata": oracle_result.metadata,
        }

        raw_data = {
            "question": question,
            "domain": domain,
            **customer_data,
        }

        # Core engine applies reasoning layers
        result = await self._core_engine.predict(
            raw_data=raw_data,
            mirofish_output=mirofish_output,
            context=context,
        )

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
        - Calibrate confidence levels (do high-confidence predictions hit high accuracy?)

        Args:
            prediction_id: Unique ID for this prediction
            confidence: Predicted confidence (0-1)
            was_correct: Whether prediction was correct
            bias_signals: List of bias signals (internal use)
            staleness_days: Age of underlying data
        """
        self._core_engine.record_outcome(
            prediction_id=prediction_id,
            confidence=confidence,
            was_correct=was_correct,
            staleness_days=staleness_days,
        )

    def check_health(self) -> Dict[str, Any]:
        """
        Check engine health: drift, calibration, tuning status.

        Returns dict with:
        - drift: Current drift detection status
        - calibration: Calibration quality metrics
        - tuned_parameters: Current parameter tuning
        """
        return self._core_engine.check_health()
