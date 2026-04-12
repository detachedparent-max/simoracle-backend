"""
Drift Detection & Adaptive Tuning

Monitors for concept drift and automatically tunes prediction parameters.

Usage:
    # Track outcomes
    tuner.record_outcome(prediction_id, confidence, bias_signals, was_correct)

    # Check for drift
    drift = detector.check_drift()
    if drift.detected:
        logger.warning(f"Drift detected: {drift.message}")

    # Get tuned parameters
    params = tuner.get_tuned_parameters()
    engine.apply_parameters(params)
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import math
import statistics

logger = logging.getLogger(__name__)


def _erf(x: float) -> float:
    """Approximation of error function for normal distribution."""
    import math

    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1 if x >= 0 else -1
    x = abs(x)

    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

    return sign * y


@dataclass
class DriftReport:
    """Result of drift detection check"""

    detected: bool
    severity: str  # "none", "mild", "moderate", "severe"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""


@dataclass
class TunedParameters:
    """Parameters adjusted by adaptive tuning"""

    bias_adjustments: Dict[str, float] = field(default_factory=dict)
    confidence_floor_adjustments: Dict[str, float] = field(default_factory=dict)
    staleness_penalty_factor: float = 1.0
    last_tuned: Optional[datetime] = None


class DriftDetector:
    """
    Detect concept drift in prediction accuracy over time.

    Drift occurs when:
    - Recent predictions are less accurate than historical
    - Accuracy suddenly drops (sudden drift)
    - Accuracy gradually degrades (gradual drift)
    - Accuracy oscillates (virtual drift)

    Methods:
    - Rolling window comparison
    - Statistical significance testing
    - Rate-of-change analysis
    """

    WINDOW_SIZES = [20, 50, 100]  # Compare recent vs older windows
    MIN_PREDICTIONS = 30

    def __init__(self):
        self.outcomes: deque = deque(maxlen=500)
        self.timestamps: deque = deque(maxlen=500)

    def record(
        self,
        prediction_id: str,
        confidence: float,
        was_correct: bool,
        timestamp: Optional[datetime] = None,
    ):
        """
        Record a prediction outcome.

        Args:
            prediction_id: Unique identifier for this prediction
            confidence: Predicted confidence (0-1)
            was_correct: Whether prediction was correct
            timestamp: When prediction was made (defaults to now)
        """
        self.outcomes.append((prediction_id, confidence, was_correct))
        self.timestamps.append(timestamp or datetime.now())

    def check_drift(self) -> DriftReport:
        """
        Check for concept drift in recent predictions.

        Returns:
            DriftReport with detected status, severity, and recommendations
        """
        if len(self.outcomes) < self.MIN_PREDICTIONS:
            return DriftReport(
                detected=False,
                severity="none",
                message=f"Insufficient data for drift detection ({len(self.outcomes)}/{self.MIN_PREDICTIONS})",
            )

        # Check each window size
        drift_detected = False
        max_severity = "none"
        details = {}

        for window_size in self.WINDOW_SIZES:
            result = self._check_window_drift(window_size)
            if result["drift_detected"]:
                drift_detected = True
                if result["severity"] == "severe":
                    max_severity = "severe"
                elif result["severity"] == "moderate" and max_severity != "severe":
                    max_severity = "moderate"
                elif result["severity"] == "mild" and max_severity == "none":
                    max_severity = "mild"
            details[f"window_{window_size}"] = result

        # Check for sudden drop (last 10 vs previous 10)
        sudden_result = self._check_sudden_drop()
        if sudden_result["detected"]:
            drift_detected = True
            if sudden_result["severity"] == "severe":
                max_severity = "severe"
            elif sudden_result["severity"] == "moderate" and max_severity != "severe":
                max_severity = "moderate"
            details["sudden_drop"] = sudden_result

        if drift_detected:
            message = f"Concept drift detected ({max_severity} severity)"
            if max_severity == "severe":
                recommended = "IMMEDIATE recalibration recommended. Recent predictions are significantly worse."
            elif max_severity == "moderate":
                recommended = "Recalibration advised. Accuracy is declining."
            else:
                recommended = "Monitor closely. Minor accuracy degradation detected."

            return DriftReport(
                detected=True,
                severity=max_severity,
                message=message,
                details=details,
                recommended_action=recommended,
            )

        return DriftReport(
            detected=False,
            severity="none",
            message="No drift detected. Accuracy is stable.",
        )

    def _check_window_drift(self, window_size: int) -> Dict[str, Any]:
        """Compare recent window accuracy to older window accuracy"""
        n = len(self.outcomes)

        if n < window_size * 2:
            return {"drift_detected": False, "reason": "Not enough data"}

        # Recent window (most recent predictions)
        recent = [o[2] for o in list(self.outcomes)[-window_size:]]
        recent_accuracy = statistics.mean(recent)

        # Older window (predictions before recent)
        older = [o[2] for o in list(self.outcomes)[-window_size * 2 : -window_size]]
        older_accuracy = statistics.mean(older)

        # Calculate drop
        accuracy_drop = older_accuracy - recent_accuracy

        # Simple statistical test (proportion comparison)
        # Using z-test approximation for proportions
        n1, n2 = len(recent), len(older)
        p1, p2 = statistics.mean(recent), statistics.mean(older)
        p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)

        if p_pooled * (1 - p_pooled) * (1 / n1 + 1 / n2) > 0:
            se = math.sqrt(p_pooled * (1 - p_pooled) * (1 / n1 + 1 / n2))
            if se > 0:
                z = (p2 - p1) / se
                # Approximate p-value (one-tailed)
                p_value = 1 - (0.5 * (1 + _erf(z / math.sqrt(2))))
                p_value = max(0.0, min(1.0, p_value))
            else:
                p_value = 1.0
        else:
            p_value = 1.0

        # Determine severity
        if accuracy_drop > 0.15 and p_value < 0.05:
            severity = "severe"
        elif accuracy_drop > 0.10 and p_value < 0.10:
            severity = "moderate"
        elif accuracy_drop > 0.05:
            severity = "mild"
        else:
            severity = "none"

        return {
            "drift_detected": severity != "none",
            "recent_accuracy": recent_accuracy,
            "older_accuracy": older_accuracy,
            "accuracy_drop": accuracy_drop,
            "p_value": p_value,
            "severity": severity,
        }

    def _check_sudden_drop(self) -> Dict[str, Any]:
        """Check for sudden accuracy drop (last 10 vs previous 10)"""
        n = len(self.outcomes)
        if n < 20:
            return {"detected": False, "reason": "Not enough data"}

        last_10 = [o[2] for o in list(self.outcomes)[-10:]]
        prev_10 = [o[2] for o in list(self.outcomes)[-20:-10]]

        last_accuracy = statistics.mean(last_10)
        prev_accuracy = statistics.mean(prev_10)
        drop = prev_accuracy - last_accuracy

        # Sudden drop = >20% accuracy drop
        detected = drop > 0.20

        return {
            "detected": detected,
            "severity": "severe" if drop > 0.30 else "moderate" if detected else "none",
            "last_10_accuracy": last_accuracy,
            "prev_10_accuracy": prev_accuracy,
            "drop": drop,
        }

    def get_accuracy_trend(self, window_size: int = 20) -> List[float]:
        """
        Get rolling accuracy over time.

        Returns list of accuracy values for each window.
        """
        if len(self.outcomes) < window_size:
            return []

        accuracies = []
        for i in range(window_size, len(self.outcomes) + 1):
            window = [o[2] for o in list(self.outcomes)[i - window_size : i]]
            accuracies.append(statistics.mean(window))

        return accuracies


class AdaptiveTuner:
    """
    Automatically tune prediction parameters based on feedback.

    Learns:
    - Which bias signals are reliable
    - How much to penalize stale data
    - Whether confidence levels are well-calibrated

    Uses exponential decay to weight recent feedback more heavily.
    """

    DEFAULT_LEARNING_RATE = 0.1
    MAX_ADJUSTMENT = 0.05  # Max single adjustment per record
    MIN_SAMPLES_FOR_TUNING = 30

    def __init__(self, learning_rate: float = DEFAULT_LEARNING_RATE):
        """
        Args:
            learning_rate: How fast to adapt (0.0-1.0, higher = faster adaptation)
        """
        self.learning_rate = learning_rate

        self.bias_signal_accuracy: Dict[str, List[bool]] = {}
        self.bias_signal_weights: Dict[str, float] = {}

        self.staleness_outcomes: Dict[int, List[bool]] = {}  # age_days -> outcomes
        self.staleness_penalty_factor = 1.0

        self.confidence_level_accuracy: Dict[str, List[bool]] = {}

        self.outcomes: List[
            Tuple[float, float, bool]
        ] = []  # (confidence, staleness, correct)

    def record_outcome(
        self,
        confidence: float,
        bias_signals: List[Dict[str, Any]],
        staleness_days: int,
        was_correct: bool,
    ):
        """
        Record a prediction outcome for tuning.

        Args:
            confidence: Predicted confidence (0-1)
            bias_signals: List of bias signals detected (with category)
            staleness_days: How old the data was
            was_correct: Whether prediction was correct
        """
        self.outcomes.append((confidence, staleness_days, was_correct))

        for signal in bias_signals:
            category = signal.get("category", "unknown")
            if category not in self.bias_signal_accuracy:
                self.bias_signal_accuracy[category] = []
            self.bias_signal_accuracy[category].append(was_correct)

        if staleness_days not in self.staleness_outcomes:
            self.staleness_outcomes[staleness_days] = []
        self.staleness_outcomes[staleness_days].append(was_correct)

        level = self._confidence_to_level(confidence)
        if level not in self.confidence_level_accuracy:
            self.confidence_level_accuracy[level] = []
        self.confidence_level_accuracy[level].append(was_correct)

        if len(self.outcomes) >= self.MIN_SAMPLES_FOR_TUNING:
            self._tune_parameters()

    def _tune_parameters(self):
        """Update tuned parameters based on recorded outcomes"""
        self._tune_bias_weights()
        self._tune_staleness_penalty()
        self._log_tuning_summary()

    def _tune_bias_weights(self):
        """Adjust bias signal weights based on accuracy"""
        for category, outcomes in self.bias_signal_accuracy.items():
            if len(outcomes) < 10:
                continue

            accuracy = statistics.mean(outcomes)

            if accuracy > 0.65:
                adjustment = self.learning_rate * 0.02
            elif accuracy < 0.45:
                adjustment = -self.learning_rate * 0.02
            else:
                adjustment = 0

            current = self.bias_signal_weights.get(category, 0)
            new_weight = current + adjustment
            new_weight = max(-0.10, min(0.10, new_weight))

            self.bias_signal_weights[category] = new_weight

    def _tune_staleness_penalty(self):
        """
        Adjust staleness penalty factor.

        If predictions on old data are less accurate, increase the penalty.
        """
        if not self.staleness_outcomes:
            return

        stale_outcomes = []
        fresh_outcomes = []

        for age, outcomes in self.staleness_outcomes.items():
            if age == 0:
                fresh_outcomes.extend(outcomes)
            elif age >= 7:
                stale_outcomes.extend(outcomes)

        if len(stale_outcomes) < 10 or len(fresh_outcomes) < 10:
            return

        stale_accuracy = statistics.mean(stale_outcomes)
        fresh_accuracy = statistics.mean(fresh_outcomes)

        if stale_accuracy < fresh_accuracy - 0.10:
            self.staleness_penalty_factor = min(
                1.5, self.staleness_penalty_factor * (1 + self.learning_rate * 0.1)
            )
        elif stale_accuracy > fresh_accuracy - 0.05:
            self.staleness_penalty_factor = max(
                1.0, self.staleness_penalty_factor * (1 - self.learning_rate * 0.05)
            )

    def _log_tuning_summary(self):
        """Log current tuning state"""
        if not self.bias_signal_weights:
            return

        non_zero = [
            (k, v) for k, v in self.bias_signal_weights.items() if abs(v) > 0.001
        ]
        if non_zero:
            adjustments = ", ".join([f"{k}:{v:+.3f}" for k, v in non_zero])
            logger.info(f"Adaptive tuning: {adjustments}")

    def get_tuned_parameters(self) -> TunedParameters:
        """Get current tuned parameters"""
        return TunedParameters(
            bias_adjustments=dict(self.bias_signal_weights),
            staleness_penalty_factor=self.staleness_penalty_factor,
            last_tuned=datetime.now(),
        )

    def get_bias_weight(self, category: str) -> float:
        """Get tuned weight for a bias category (0 if not tuned)"""
        return self.bias_signal_weights.get(category, 0.0)

    def get_staleness_penalty_factor(self) -> float:
        """Get current staleness penalty factor"""
        return getattr(self, "staleness_penalty_factor", 1.0)

    def _confidence_to_level(self, confidence: float) -> str:
        """Convert numeric confidence to level string"""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.6:
            return "moderate"
        elif confidence >= 0.4:
            return "guarded"
        else:
            return "low"

    def get_calibration_report(self) -> Dict[str, Any]:
        """
        Get calibration report showing confidence level accuracy.

        Ideally: high confidence → high accuracy, low confidence → low accuracy
        """
        report = {"total_outcomes": len(self.outcomes), "confidence_levels": {}}

        for level, outcomes in self.confidence_level_accuracy.items():
            accuracy = statistics.mean(outcomes)
            expected_accuracy = {
                "high": 0.80,
                "moderate": 0.60,
                "guarded": 0.40,
                "low": 0.20,
            }.get(level, 0.50)

            gap = accuracy - expected_accuracy

            report["confidence_levels"][level] = {
                "n": len(outcomes),
                "actual_accuracy": accuracy,
                "expected_accuracy": expected_accuracy,
                "gap": gap,
                "well_calibrated": abs(gap) < 0.15,
            }

        return report


class PredictionHealthMonitor:
    """
    Combined drift detection + adaptive tuning.

    Use this for production monitoring.
    """

    def __init__(self, learning_rate: float = 0.1):
        self.drift_detector = DriftDetector()
        self.adaptive_tuner = AdaptiveTuner(learning_rate)
        self.alerts: List[Dict] = []

    def record(
        self,
        prediction_id: str,
        confidence: float,
        bias_signals: List[Dict],
        staleness_days: int,
        was_correct: bool,
    ):
        """
        Record a prediction outcome for monitoring.
        """
        self.drift_detector.record(prediction_id, confidence, was_correct)
        self.adaptive_tuner.record_outcome(
            confidence, bias_signals, staleness_days, was_correct
        )

    def check_health(self) -> Dict[str, Any]:
        """
        Check overall prediction health.

        Returns dict with:
        - drift: DriftReport
        - calibration: calibration report
        - tuned_params: current parameters
        - alerts: list of active alerts
        """
        drift_report = self.drift_detector.check_drift()

        health = {
            "timestamp": datetime.now(),
            "drift": {
                "detected": drift_report.detected,
                "severity": drift_report.severity,
                "message": drift_report.message,
                "action": drift_report.recommended_action,
            },
            "calibration": self.adaptive_tuner.get_calibration_report(),
            "tuned_parameters": {
                "bias_adjustments": self.adaptive_tuner.get_tuned_parameters().bias_adjustments,
                "staleness_penalty_factor": self.adaptive_tuner.get_staleness_penalty_factor(),
            },
            "accuracy_trend": self.drift_detector.get_accuracy_trend(),
        }

        if drift_report.detected:
            health["alerts"] = [
                {
                    "type": "drift",
                    "severity": drift_report.severity,
                    "message": drift_report.message,
                    "action": drift_report.recommended_action,
                }
            ]

        return health
