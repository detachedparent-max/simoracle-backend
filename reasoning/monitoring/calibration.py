"""
Calibration Monitoring

Track if confidence estimates match actual accuracy.
Based on Expected Calibration Error (ECE) from NVIDIA NeMo research.

Usage:
    monitor = CalibrationMonitor()

    # After making a prediction
    result = engine.predict(...)
    monitor.record(confidence=result.confidence, was_correct=outcome)

    # Periodically check calibration
    ece = monitor.compute_ece()
    if ece > 0.15:
        logger.warning(f"Engine miscalibrated: ECE={ece:.3f}")
"""

import logging
from typing import List, Tuple, Optional, Dict
import numpy as np

logger = logging.getLogger(__name__)


class CalibrationMonitor:
    """Track if confidence estimates match actual accuracy"""

    def __init__(self):
        """Initialize empty prediction log"""
        self.predictions: List[Tuple[float, bool]] = []

    def record(self, confidence: float, was_correct: bool):
        """
        Log a prediction with its outcome.

        Args:
            confidence: Predicted confidence (0-1)
            was_correct: Whether prediction was correct (ground truth)
        """
        self.predictions.append((confidence, was_correct))
        logger.debug(f"Recorded: confidence={confidence:.2f}, correct={was_correct}")

    def compute_ece(self, bins: int = 10) -> Optional[float]:
        """
        Compute Expected Calibration Error.

        Bins predictions by confidence level, then measures:
        For each bin: |predicted_confidence - actual_accuracy|

        ECE = average gap across all bins
        - ECE = 0.0 → perfectly calibrated
        - ECE = 0.15 → acceptable (±15% error)
        - ECE > 0.2 → miscalibrated (overconfident or underconfident)

        Args:
            bins: Number of confidence bins (default 10 = deciles)

        Returns:
            ECE score (0-1), or None if insufficient data
        """
        if len(self.predictions) < bins:
            logger.warning(f"Insufficient predictions ({len(self.predictions)}) for ECE computation (need >{bins})")
            return None

        confidences = np.array([p[0] for p in self.predictions])
        correctness = np.array([float(p[1]) for p in self.predictions])

        ece_scores = []

        for i in range(bins):
            lower = i / bins
            upper = (i + 1) / bins

            # Find predictions in this confidence bin
            mask = (confidences >= lower) & (confidences < upper)

            if mask.sum() > 0:
                # For this bin: gap between predicted confidence and actual accuracy
                predicted_conf = confidences[mask].mean()
                actual_acc = correctness[mask].mean()
                gap = abs(predicted_conf - actual_acc)
                ece_scores.append(gap)

        ece = float(np.mean(ece_scores)) if ece_scores else None
        logger.debug(f"ECE computed: {ece:.3f} ({len(self.predictions)} predictions across {len(ece_scores)} bins)")

        return ece

    def is_miscalibrated(self, threshold: float = 0.15) -> Optional[bool]:
        """
        Check if engine is miscalibrated (ECE > threshold).

        Args:
            threshold: ECE threshold (default 0.15 = acceptable)

        Returns:
            True if miscalibrated, False if well-calibrated, None if insufficient data
        """
        ece = self.compute_ece()
        if ece is None:
            return None

        is_bad = ece > threshold
        if is_bad:
            logger.warning(f"Engine is miscalibrated! ECE={ece:.3f} > threshold={threshold}")

        return is_bad

    def is_overconfident(self) -> Optional[bool]:
        """
        Check if engine tends to be overconfident.

        Returns True if mean_accuracy < mean_confidence (predicts too high)
        """
        if len(self.predictions) < 10:
            return None

        confidences = np.array([p[0] for p in self.predictions])
        correctness = np.array([float(p[1]) for p in self.predictions])

        return correctness.mean() < confidences.mean()

    def is_underconfident(self) -> Optional[bool]:
        """
        Check if engine tends to be underconfident.

        Returns True if mean_accuracy > mean_confidence (predicts too low)
        """
        if len(self.predictions) < 10:
            return None

        confidences = np.array([p[0] for p in self.predictions])
        correctness = np.array([float(p[1]) for p in self.predictions])

        return correctness.mean() > confidences.mean()

    def get_stats(self) -> Dict[str, float]:
        """
        Get comprehensive calibration statistics.

        Returns:
            Dict with:
            - n_predictions: Total predictions logged
            - mean_confidence: Average predicted confidence
            - mean_accuracy: Actual accuracy (% correct)
            - ece: Expected Calibration Error
            - overconfidence_gap: mean_confidence - mean_accuracy
            - confidence_std: Standard deviation of confidences
            - accuracy_std: Standard deviation of correctness
        """
        if not self.predictions:
            return {
                "n_predictions": 0,
                "message": "No predictions yet"
            }

        confidences = np.array([p[0] for p in self.predictions])
        correctness = np.array([float(p[1]) for p in self.predictions])

        mean_conf = float(confidences.mean())
        mean_acc = float(correctness.mean())

        return {
            "n_predictions": len(self.predictions),
            "mean_confidence": mean_conf,
            "mean_accuracy": mean_acc,
            "confidence_std": float(confidences.std()),
            "accuracy_std": float(correctness.std()),
            "ece": self.compute_ece(),
            "overconfidence_gap": mean_conf - mean_acc,
            "is_overconfident": self.is_overconfident(),
            "is_underconfident": self.is_underconfident(),
        }

    def reset(self):
        """Clear all logged predictions"""
        self.predictions = []
        logger.info("CalibrationMonitor reset")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"CalibrationMonitor(n={stats.get('n_predictions', 0)}, ece={stats.get('ece', 'N/A')})"
