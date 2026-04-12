"""
Behavioral Bias Detector

Detects cognitive biases that inflate or deflate probabilities:
- Anchoring: Initial bid/offer sticks too much
- Overconfidence: Expert says 90% sure when they shouldn't be
- Recency: Recent wins overweighted
- Sunk costs: Large past investments bias toward continuing
- Hindsight: Knowing outcome makes it seem obvious

Domain-agnostic: works on HR, M&A, law, real estate, startup, insurance, supply chain.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BiasSignal:
    """Single bias detection with adjustment"""
    category: str  # "anchoring", "overconfidence", etc.
    adjustment: float  # -0.20 to +0.20
    signal: str  # Human-readable explanation
    source: str = "behavioral_bias"


class BehavioralBiasDetector:
    """Detect cognitive biases in decision data"""

    def detect(self, raw_data: Dict[str, Any], context: Dict[str, Any]) -> List[BiasSignal]:
        """
        Detect behavioral biases in raw data and context.

        Returns list of BiasSignal objects, each with:
        - category: type of bias
        - adjustment: probability adjustment (-0.20 to +0.20)
        - signal: explanation of the bias
        """
        signals = []

        # Check 1: Anchoring bias
        anchoring = self._detect_anchoring(raw_data, context)
        if anchoring:
            signals.append(anchoring)

        # Check 2: Overconfidence bias
        overconf = self._detect_overconfidence(context)
        if overconf:
            signals.append(overconf)

        # Check 3: Recency bias
        recency = self._detect_recency(raw_data, context)
        if recency:
            signals.append(recency)

        # Check 4: Sunk cost bias
        sunk_cost = self._detect_sunk_costs(context)
        if sunk_cost:
            signals.append(sunk_cost)

        # Check 5: Hindsight bias
        hindsight = self._detect_hindsight(context)
        if hindsight:
            signals.append(hindsight)

        return signals

    def _detect_anchoring(self, raw_data: Dict, context: Dict) -> BiasSignal | None:
        """
        Detect anchoring: initial bid/offer sticks too much.

        Universal patterns:
        - HR: initial salary offer anchors expectations
        - M&A: initial valuation anchors negotiation
        - Law: initial settlement offer anchors final deal
        - Real Estate: list price anchors perceived value
        """
        # Check if there's a numeric anchor in context
        initial_anchor = context.get("initial_anchor")
        current_value = context.get("current_value")

        if initial_anchor and current_value:
            gap = abs(current_value - initial_anchor) / initial_anchor if initial_anchor != 0 else 0

            # Large gap (>30%) indicates anchor stuck
            if gap > 0.30:
                adjustment = -0.08  # Reduce probability for anchoring effect
                return BiasSignal(
                    category="anchoring",
                    adjustment=adjustment,
                    signal=f"Large gap between initial ({initial_anchor}) and current ({current_value}) suggests anchoring effect"
                )

        return None

    def _detect_overconfidence(self, context: Dict) -> BiasSignal | None:
        """
        Detect overconfidence: expert claims too high certainty.

        Universal pattern: When expert_confidence > 0.85, they're likely overestimating.
        Research shows experts are overconfident ~60% of the time.
        """
        expert_confidence = context.get("expert_confidence", 0)

        if expert_confidence > 0.85:
            # Apply correction factor based on literature (typically -10-15% adjustment)
            adjustment = -0.12
            return BiasSignal(
                category="overconfidence",
                adjustment=adjustment,
                signal=f"Expert confidence {expert_confidence:.0%} indicates likely overestimation (typical correction: -12%)"
            )

        return None

    def _detect_recency(self, raw_data: Dict, context: Dict) -> BiasSignal | None:
        """
        Detect recency bias: recent wins overweighted.

        Universal patterns:
        - HR: recent hiring successes inflate next hire probability
        - M&A: recent successful deals inflate risk estimates
        - Law: recent case wins inflate win probability estimates
        - Real Estate: recent sales inflate comps expectations
        """
        recent_successes = context.get("recent_successes", 0)
        recent_failures = context.get("recent_failures", 0)
        total_history = context.get("total_history", 1)

        if recent_successes > 0 and total_history > 0:
            success_rate = recent_successes / (recent_successes + recent_failures) if (recent_successes + recent_failures) > 0 else 0
            historical_rate = context.get("historical_success_rate", 0.5)

            # If recent rate is higher than historical, adjust down
            if success_rate > historical_rate + 0.10:  # >10 percentage points higher
                adjustment = -0.05
                return BiasSignal(
                    category="recency",
                    adjustment=adjustment,
                    signal=f"Recent success rate {success_rate:.0%} exceeds historical {historical_rate:.0%}; recent wins may not be representative"
                )

        return None

    def _detect_sunk_costs(self, context: Dict) -> BiasSignal | None:
        """
        Detect sunk cost bias: large past investments bias toward continuing.

        Universal pattern: When sunk_cost_amount > $1M, decision-maker is likely
        to continue investment despite poor prospects.
        """
        sunk_cost_amount = context.get("sunk_cost_amount", 0)

        if sunk_cost_amount > 1_000_000:
            # Larger sunk costs = stronger bias
            # $1M-5M: -10%, $5M-20M: -12%, $20M+: -15%
            if sunk_cost_amount < 5_000_000:
                adjustment = -0.10
            elif sunk_cost_amount < 20_000_000:
                adjustment = -0.12
            else:
                adjustment = -0.15

            return BiasSignal(
                category="sunk_cost",
                adjustment=adjustment,
                signal=f"Large sunk costs (${sunk_cost_amount:,.0f}) bias toward continuing despite poor prospects"
            )

        return None

    def _detect_hindsight(self, context: Dict) -> BiasSignal | None:
        """
        Detect hindsight bias: knowing outcome makes it seem obvious.

        Universal pattern: When we know the outcome, we retroactively claim
        we knew it all along. Probability estimates become inflated.
        """
        known_outcome = context.get("known_outcome")
        made_prediction = context.get("made_prediction")

        # Only detect if this is retrospective analysis (outcome is known)
        # but we're being asked to re-estimate probability
        if known_outcome is not None and made_prediction is not None:
            # Hindsight bias typically inflates perceived certainty by 10-15%
            adjustment = -0.10
            return BiasSignal(
                category="hindsight",
                adjustment=adjustment,
                signal="Known outcome creates hindsight bias; re-estimated probability is likely inflated"
            )

        return None
