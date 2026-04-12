"""
Universal Prediction Engine

Takes ANY raw data + MiroFish probability → returns calibrated prediction + reasoning

Domain-agnostic: works for HR, M&A, Law, Real Estate, Startups, Insurance, Supply Chain
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pprint import pformat

from .layers.behavioral_bias import BehavioralBiasDetector, BiasSignal
from .layers.temporal import TemporalAdjuster, TemporalSignal
from .layers.confidence_cal import ConfidenceCalibrator, ConfidenceResult
from .layers.validation import InputValidator, InputValidationReport, ValidationLevel
from .blender import ProbabilityBlender
from .schemas import ReasoningOutput, ConfidenceLevel, LayerExplanation
from .monitoring.calibration import CalibrationMonitor
from .monitoring.drift_tuning import PredictionHealthMonitor, DriftReport

logger = logging.getLogger(__name__)


class UniversalPredictionEngine:
    """
    Universal calibration engine.

    Takes MiroFish base probability and applies reasoning adjustments.
    Works on any domain (HR, M&A, Law, Real Estate, Startup, Insurance, Supply Chain).

    Usage:
        engine = UniversalPredictionEngine()
        result = await engine.predict(
            raw_data={"candidate_resume": "...", "role_requirements": "..."},
            mirofish_output={"probability": 0.72, "simulations": 1000000},
            context={"stage": "early_investigation", "expert_confidence": 0.88}
        )

    Returns:
        ReasoningOutput with:
        - base_probability: 0.72 (from MiroFish)
        - calibrated_probability: 0.55 (after reasoning)
        - confidence: 0.68 (how sure we are)
        - confidence_level: "MODERATE"
        - reasoning_chain: List of adjustments + explanations
        - recommendation: Actionable advice
    """

    def __init__(self):
        """Initialize reasoning components"""
        self.bias_detector = BehavioralBiasDetector()
        self.temporal_adjuster = TemporalAdjuster()
        self.confidence_calibrator = ConfidenceCalibrator()
        self.validator = InputValidator()
        self.blender = ProbabilityBlender()
        self.calibration_monitor = CalibrationMonitor()
        self.health_monitor = PredictionHealthMonitor()
        self._tuned_bias_adjustments: Dict[str, float] = {}

        logger.info("✅ UniversalPredictionEngine initialized")

    async def predict(
        self,
        raw_data: Dict[str, Any],
        mirofish_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningOutput:
        """
        Generate calibrated prediction with reasoning.

        Args:
            raw_data: Customer's input data (resume, target company, case details, property, etc.)
            mirofish_output: Output from MiroFish simulation
                {
                    "probability": 0.72,
                    "simulations": 1000000,
                    "confidence_interval": (0.65, 0.79),
                    ...
                }
            context: Optional additional context
                {
                    "stage": "early_investigation",
                    "expert_confidence": 0.88,
                    "data_age_days": 15,
                    "sunk_cost_amount": 500000,
                    ...
                }

        Returns:
            ReasoningOutput with calibrated probability + reasoning + confidence
        """

        context = context or {}

        # Step 0: Validate input data
        validation_report = self.validator.validate(raw_data, context)

        if validation_report.level == ValidationLevel.FAIL:
            raise ValueError(
                f"Input validation failed: {validation_report.summary}. "
                f"Issues: {[r.message for r in validation_report.failures]}"
            )

        # Log warnings but continue
        for warning in validation_report.warnings:
            logger.warning(f"Validation warning: {warning.message}")

        # Extract base probability from MiroFish
        base_probability = mirofish_output.get("probability", 0.5)
        if not (0 <= base_probability <= 1):
            raise ValueError(f"Invalid probability: {base_probability}")

        logger.info(f"🔄 Processing: Base probability = {base_probability:.0%}")

        # Step 1: Detect behavioral biases
        behavioral_signals = self.bias_detector.detect(raw_data, context)
        behavioral_adjustments = [s.adjustment for s in behavioral_signals]

        logger.info(f"   Behavioral biases found: {len(behavioral_signals)}")
        for signal in behavioral_signals:
            logger.debug(
                f"     - {signal.category}: {signal.adjustment:+.0%} ({signal.signal})"
            )

        # Step 2: Apply temporal adjustments
        temporal_signals = self.temporal_adjuster.adjust(raw_data, context)
        temporal_adjustments = [s.adjustment for s in temporal_signals]

        logger.info(f"   Temporal adjustments: {len(temporal_signals)}")
        for signal in temporal_signals:
            logger.debug(
                f"     - {signal.category}: {signal.adjustment:+.0%} ({signal.signal})"
            )

        # Step 3: Blend adjustments into final probability
        calibrated_probability = self.blender.blend(
            base_probability, behavioral_adjustments + temporal_adjustments
        )

        logger.info(f"   Calibrated probability: {calibrated_probability:.0%}")

        # Step 4: Calculate confidence
        confidence_result = self.confidence_calibrator.calibrate(
            raw_data, context, mirofish_output
        )

        # Step 5: Generate reasoning chain
        reasoning_chain = self._compile_reasoning_chain(
            behavioral_signals, temporal_signals
        )

        # Step 6: Generate recommendation
        recommendation = self._generate_recommendation(
            calibrated_probability, confidence_result
        )

        # Step 7: Generate caveats
        caveats = self._generate_caveats(raw_data, context)

        # Add staleness caveat if confidence was capped
        staleness_ceiling = None
        data_age = context.get("data_age_days", 0)
        if data_age > 0:
            staleness_ceiling = self.validator.get_staleness_ceiling(data_age)
            if staleness_ceiling < 1.0:
                caveats.append(
                    f"Data is {data_age} days old. Maximum confidence capped at {staleness_ceiling:.0%}."
                )

        # Create output
        result = ReasoningOutput(
            base_probability=base_probability,
            calibrated_probability=calibrated_probability,
            confidence=confidence_result.confidence,
            confidence_level=self._to_confidence_level(confidence_result.confidence),
            reasoning_chain=reasoning_chain,
            recommendation=recommendation,
            caveats=caveats,
            timestamp=datetime.now(),
            validation_level=validation_report.level.value,
            validation_warnings=[w.message for w in validation_report.warnings],
            staleness_ceiling=staleness_ceiling
            if staleness_ceiling and staleness_ceiling < 1.0
            else None,
            oracle_type=context.get("oracle_type", "unknown"),
            data_summary=self._summarize_data(raw_data),
        )

        logger.info(f"✅ Prediction complete")
        logger.info(
            f"   Base: {result.base_probability:.0%} → Calibrated: {result.calibrated_probability:.0%}"
        )
        logger.info(
            f"   Confidence: {result.confidence_level.value} ({result.confidence:.0%})"
        )

        return result

    def _compile_reasoning_chain(
        self,
        behavioral_signals: List[BiasSignal],
        temporal_signals: List[TemporalSignal],
    ) -> List[LayerExplanation]:
        """Combine all signals into reasoning chain"""
        chain = []

        for signal in behavioral_signals:
            chain.append(
                LayerExplanation(
                    layer_name=f"behavioral_bias_{signal.category}",
                    adjustment=signal.adjustment,
                    explanation=signal.signal,
                    details={"category": signal.category, "source": signal.source},
                )
            )

        for signal in temporal_signals:
            chain.append(
                LayerExplanation(
                    layer_name=f"temporal_{signal.category}",
                    adjustment=signal.adjustment,
                    explanation=signal.signal,
                    details={"category": signal.category, "source": signal.source},
                )
            )

        return chain

    def _generate_recommendation(
        self, calibrated_prob: float, confidence_result: ConfidenceResult
    ) -> str:
        """Generate actionable recommendation"""
        conf = confidence_result.confidence

        # Low confidence always overrides
        if conf < 0.4:
            return "⚠️  INSUFFICIENT DATA: Confidence too low to recommend. Need more information before deciding."

        # High probability
        if calibrated_prob > 0.75:
            if conf > 0.7:
                return "✅ STRONG YES: High probability and confidence. Proceed with confidence."
            else:
                return "✅ LIKELY YES: Probability is high, but confidence is moderate. Validate key assumptions before proceeding."

        # Moderate-high probability
        if calibrated_prob > 0.60:
            if conf > 0.7:
                return "👍 LEAN YES: Probable outcome. Proceed, but monitor key risk factors."
            else:
                return "👍 LEAN YES (Cautious): Probable, but confidence is moderate. Identify and mitigate specific risks."

        # Uncertain
        if calibrated_prob > 0.40 and calibrated_prob <= 0.60:
            return "❓ UNCERTAIN: Too much uncertainty. Recommend additional diligence or wait for more data."

        # Moderate-low probability
        if calibrated_prob > 0.25:
            if conf > 0.7:
                return "👎 LEAN NO: Low probability. Significant risks identified. Recommend against."
            else:
                return "👎 LEAN NO (Cautious): Low probability, but confidence is moderate. Consider deeper analysis."

        # Low probability
        return "❌ STRONG NO: Very low probability. Recommend against. High risk of failure."

    def _generate_caveats(self, raw_data: Dict, context: Dict) -> List[str]:
        """Generate list of known limitations"""
        caveats = []

        # Data-based caveats
        data_keys = raw_data.keys() if isinstance(raw_data, dict) else []
        if len(data_keys) < 3:
            caveats.append(
                "Limited data provided: More information would improve prediction"
            )

        # Context-based caveats
        if not context.get("historical_accuracy"):
            caveats.append(
                "No historical data for calibration: Prediction assumes general population patterns"
            )

        if context.get("high_volatility"):
            caveats.append(
                "Market/environment is volatile: Predictions less stable in turbulent conditions"
            )

        if context.get("data_age_days", 0) > 30:
            caveats.append(
                f"Data is {context.get('data_age_days')} days old: Market/situation may have changed"
            )

        if context.get("expert_variance", 0) > 0.4:
            caveats.append(
                "Expert opinions diverge significantly: Uncertain consensus on outcome"
            )

        if context.get("situation_uniqueness", 0) > 0.7:
            caveats.append(
                "Situation is unique/rare: Limited historical precedent to calibrate against"
            )

        # Always include this caveat
        caveats.append(
            "This prediction reflects historical patterns and expert judgment, not certainty"
        )

        return caveats

    def _summarize_data(self, raw_data: Dict) -> Dict[str, Any]:
        """Create brief summary of input data"""
        return {
            "data_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else [],
            "data_size": len(str(raw_data)),
        }

    def _to_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to qualitative level"""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.4:
            return ConfidenceLevel.GUARDED
        else:
            return ConfidenceLevel.LOW

    def record_outcome(self, confidence: float, was_correct: bool):
        """
        Record prediction outcome for calibration monitoring.

        Call this after receiving ground truth to track calibration.

        Args:
            confidence: The confidence score from the prediction
            was_correct: Whether the prediction was correct
        """
        self.calibration_monitor.record(confidence, was_correct)

    def get_calibration_stats(self) -> Dict[str, Any]:
        """Get current calibration statistics"""
        return self.calibration_monitor.get_stats()

    def get_calibration_error(self) -> Optional[float]:
        """Get Expected Calibration Error (ECE)"""
        return self.calibration_monitor.compute_ece()

    def record_full_outcome(
        self,
        prediction_id: str,
        confidence: float,
        bias_signals: List[BiasSignal],
        staleness_days: int,
        was_correct: bool,
    ):
        """
        Record outcome for drift detection + adaptive tuning.

        Use this for production monitoring - records to both calibration
        monitor and health monitor.

        Args:
            prediction_id: Unique ID for this prediction
            confidence: Confidence score from prediction
            bias_signals: List of BiasSignal objects detected
            staleness_days: How old the data was
            was_correct: Whether prediction was correct
        """
        self.calibration_monitor.record(confidence, was_correct)

        signal_dicts = [
            {"category": s.category, "adjustment": s.adjustment} for s in bias_signals
        ]

        self.health_monitor.record(
            prediction_id=prediction_id,
            confidence=confidence,
            bias_signals=signal_dicts,
            staleness_days=staleness_days,
            was_correct=was_correct,
        )

    def check_drift(self) -> DriftReport:
        """
        Check for concept drift in predictions.

        Returns DriftReport with detected status and severity.
        """
        return self.health_monitor.drift_detector.check_drift()

    def check_health(self) -> Dict[str, Any]:
        """
        Get comprehensive health report.

        Returns dict with:
        - drift detection status
        - calibration report by confidence level
        - tuned parameters
        - accuracy trend
        """
        return self.health_monitor.check_health()

    def get_tuned_bias_adjustment(self, category: str) -> float:
        """
        Get tuned adjustment for a bias category.

        Returns 0 if not yet tuned.
        """
        return self.health_monitor.adaptive_tuner.get_bias_weight(category)

    def get_tuned_staleness_factor(self, data_age_days: int) -> float:
        """
        Get tuned staleness factor.

        Applies penalty factor if recent stale-data predictions were wrong.
        """
        base_ceiling = self.validator.get_staleness_ceiling(data_age_days)
        penalty_factor = (
            self.health_monitor.adaptive_tuner.get_staleness_penalty_factor()
        )
        return base_ceiling * penalty_factor


# Convenience function for async usage
async def create_engine() -> UniversalPredictionEngine:
    """Factory function to create engine"""
    return UniversalPredictionEngine()
