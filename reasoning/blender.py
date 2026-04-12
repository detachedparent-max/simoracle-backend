"""
Probability Blender

Combines MiroFish base probability with reasoning adjustments.

Strategy: Weighted average with conservative decay toward base.
- MiroFish ran 1M simulations on real data
- Reasoning adjustments are heuristic-based
- Trust MiroFish more (70%), adjust less aggressively (30%)
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class ProbabilityBlender:
    """Blend base probability with adjustment signals"""

    # Tuning parameters
    DECAY_FACTOR = 0.70  # Trust MiroFish 70%, reasoning adjustments 30%
    MAX_ADJUSTMENT = 0.20  # No single adjustment can move probability >20%
    MIN_PROBABILITY = 0.01  # Never return 0% (always leave room for surprise)
    MAX_PROBABILITY = 0.99  # Never return 100% (always leave room for doubt)

    def blend(
        self,
        base_probability: float,
        adjustments: List[float]
    ) -> float:
        """
        Blend base probability with adjustments.

        Args:
            base_probability: From MiroFish (e.g., 0.72)
            adjustments: List of numeric adjustments from reasoning layers
                        (e.g., [-0.08, -0.12, -0.05, -0.10])

        Returns:
            Calibrated probability (clamped to [0.01, 0.99])
        """

        if not adjustments:
            # No adjustments: return base as-is (clamped)
            return self._clamp(base_probability)

        # Step 1: Clamp individual adjustments (no wild swings)
        clamped = [max(-self.MAX_ADJUSTMENT, min(self.MAX_ADJUSTMENT, a)) for a in adjustments]

        # Step 2: Average the adjustments
        avg_adjustment = sum(clamped) / len(clamped)

        # Step 3: Apply decay factor (conservative blending)
        # Only move 30% of the way toward the adjustment (70% stay with MiroFish)
        adjusted = base_probability + (avg_adjustment * (1 - self.DECAY_FACTOR))

        # Step 4: Clamp to [MIN, MAX]
        final = self._clamp(adjusted)

        logger.debug(
            f"Blend: base={base_probability:.2f} + adjustments={clamped} "
            f"(avg={avg_adjustment:.3f}) × decay={1-self.DECAY_FACTOR:.2f} → {final:.2f}"
        )

        return final

    def _clamp(self, probability: float) -> float:
        """Clamp probability to valid range [0.01, 0.99]"""
        return max(self.MIN_PROBABILITY, min(self.MAX_PROBABILITY, probability))
