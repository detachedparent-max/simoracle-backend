"""
Confidence Calibrator

Measures confidence separately from probability.

Key insight: We might be:
- 95% confident in a 65% probability (tight, well-supported estimate)
- 30% confident in a 65% probability (loose, weakly-supported estimate)

Confidence factors:
1. Data completeness: How much data do we have? (0-1)
2. Historical accuracy: How well does this type prediction work? (0-1)
3. Expert variance: Do experts agree? (0-1)
4. Situation uniqueness: Is this a common scenario? (0-1)

Domain-agnostic: works on any domain.
"""

import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import statistics
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceResult:
    """Confidence calibration output"""

    confidence: float  # 0-1, how sure are we
    factors: List[Tuple[str, float]]  # List of (name, score) tuples
    confidence_level: str  # "HIGH", "MODERATE", "GUARDED", "LOW"


class ConfidenceCalibrator:
    """Calculate confidence separate from probability"""

    STALENESS_CEILINGS = {
        0: 1.0,  # Fresh data: no penalty
        1: 0.95,  # 1 day old: max 95% confidence
        3: 0.85,  # 3 days: max 85%
        7: 0.75,  # 1 week: max 75%
        14: 0.65,  # 2 weeks: max 65%
        30: 0.50,  # 1 month: max 50%
    }

    def calibrate(
        self,
        raw_data: Dict[str, Any],
        context: Dict[str, Any],
        mirofish_output: Dict[str, Any],
    ) -> ConfidenceResult:
        """
        Calibrate confidence based on 4 factors + staleness ceiling.

        Returns:
        - confidence: numeric score (0-1)
        - factors: breakdown of contributing factors
        - confidence_level: qualitative level (HIGH/MODERATE/GUARDED/LOW)
        """

        factors = []

        # Factor 1: Data completeness
        completeness = self._assess_data_completeness(raw_data, context)
        factors.append(("data_completeness", completeness))

        # Factor 2: Historical accuracy for this type of prediction
        hist_acc = context.get("historical_accuracy", 0.65)
        hist_acc = max(0.0, min(1.0, hist_acc))  # Clamp to 0-1
        factors.append(("historical_accuracy", hist_acc))

        # Factor 3: Expert agreement (low variance = high confidence)
        expert_agreement = self._assess_expert_agreement(context)
        factors.append(("expert_agreement", expert_agreement))

        # Factor 4: Situation commonality (rare situations = lower confidence)
        situation_commonality = self._assess_situation_commonality(context)
        factors.append(("situation_commonality", situation_commonality))

        # Combine factors using harmonic mean (conservative: if ANY is low, confidence is low)
        confidence_scores = [f[1] for f in factors]
        base_confidence = self._harmonic_mean(confidence_scores)

        # Apply staleness ceiling
        data_age = context.get("data_age_days", 0)
        staleness_ceiling = self._get_staleness_ceiling(data_age)

        if base_confidence > staleness_ceiling:
            factors.append(("staleness_ceiling", staleness_ceiling))
            base_confidence = staleness_ceiling

        # Convert to qualitative level
        confidence_level = self._to_qualitative(base_confidence)

        return ConfidenceResult(
            confidence=base_confidence,
            factors=factors,
            confidence_level=confidence_level,
        )

    def _get_staleness_ceiling(self, data_age_days: int) -> float:
        """
        Get staleness ceiling - max confidence allowed based on data age.

        Even if everything else looks perfect, you can't claim high confidence
        on stale data. This is the confidence ceiling, not a direct reduction.
        """
        for max_age, ceiling in sorted(self.STALENESS_CEILINGS.items(), reverse=True):
            if data_age_days >= max_age:
                return ceiling
        return self.STALENESS_CEILINGS[0]  # Fresh data = 1.0

    def _assess_data_completeness(self, raw_data: Dict, context: Dict) -> float:
        """
        Assess how complete the input data is.

        Universal heuristics:
        - Number of data fields (more = more complete)
        - Data size in bytes (more text = richer)
        - Explicit completeness score if provided
        """
        # Check for explicit completeness score
        if "data_completeness" in context:
            return max(0.0, min(1.0, context["data_completeness"]))

        # Otherwise estimate from data size
        data_keys = raw_data.keys() if isinstance(raw_data, dict) else []
        data_size = len(str(raw_data))

        # Heuristic: 3-5 fields = 0.5, 5-10 = 0.7, 10+ = 0.9
        field_score = min(len(data_keys) / 10, 1.0) * 0.5 + 0.3
        # Heuristic: <500 chars = 0.3, 500-2000 = 0.6, 2000+ = 0.85
        size_score = min(data_size / 2000, 1.0) * 0.55 + 0.3

        # Average the two
        completeness = (field_score + size_score) / 2
        return max(0.0, min(1.0, completeness))

    def _assess_expert_agreement(self, context: Dict) -> float:
        """
        Assess expert agreement (low variance = high agreement = high confidence).

        Universal pattern: If experts agree, we're confident. If they disagree, less confident.

        Input: expert_variance (0-1, where 0 = perfect agreement, 1 = total disagreement)
        """
        expert_variance = context.get("expert_variance", 0.3)
        expert_variance = max(0.0, min(1.0, expert_variance))

        # Invert: low variance = high score
        # variance 0.0 → score 1.0
        # variance 0.5 → score 0.5
        # variance 1.0 → score 0.0
        expert_agreement = 1.0 - expert_variance

        return expert_agreement

    def _assess_situation_commonality(self, context: Dict) -> float:
        """
        Assess how common/typical this situation is.

        Universal pattern: Common situations = we have more precedent = higher confidence.
        Rare situations = less precedent = lower confidence.

        Input: situation_uniqueness (0-1, where 0 = very common, 1 = very rare)
        """
        situation_uniqueness = context.get("situation_uniqueness", 0.5)
        situation_uniqueness = max(0.0, min(1.0, situation_uniqueness))

        # Invert and dampen: uniqueness 0.0 → score 0.95, uniqueness 1.0 → score 0.45
        # This gives 50 percentage points range
        situation_commonality = 0.95 - (situation_uniqueness * 0.5)

        return max(0.45, min(0.95, situation_commonality))

    def _harmonic_mean(self, values: List[float]) -> float:
        """
        Calculate harmonic mean weighted by agreement (inverse-disagreement).

        Harmonic mean is conservative: if ANY value is low, the mean is low.
        Weighted by inverse-disagreement (from Confidence-Engine research):
        If factors agree, confidence stays high. If they disagree, confidence drops.

        Formula:
        - Base harmonic: H = n / (1/x1 + 1/x2 + ... + 1/xn)
        - Weighted by agreement: H / (1 + std_dev)
        """
        if not values or all(v == 0 for v in values):
            return 0.0

        # Filter out zeros (would cause division by zero in harmonic mean)
        non_zero = [v for v in values if v > 0]
        if not non_zero:
            return 0.0

        try:
            base_harmonic = statistics.harmonic_mean(non_zero)
        except statistics.StatisticsError:
            # Fallback to regular mean if harmonic fails
            base_harmonic = sum(non_zero) / len(non_zero)

        # Weight down by disagreement (inverse-disagreement formula from research)
        # Perfect agreement (std=0) → confidence stays at base_harmonic
        # High disagreement (std=0.5) → confidence drops significantly
        disagreement = float(np.std(non_zero))
        weighted = base_harmonic / (1.0 + disagreement)

        return weighted

    def _to_qualitative(self, confidence: float) -> str:
        """Convert numeric confidence to qualitative level"""
        if confidence >= 0.80:
            return "HIGH"
        elif confidence >= 0.60:
            return "MODERATE"
        elif confidence >= 0.40:
            return "GUARDED"
        else:
            return "LOW"
