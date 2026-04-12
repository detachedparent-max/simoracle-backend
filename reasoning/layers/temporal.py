"""
Temporal Adjuster

Accounts for time-based factors that affect prediction accuracy:
- Information decay: Older data becomes stale
- Decision lifecycle: Early stage = higher uncertainty, post-close = validation
- Market volatility: Turbulent conditions reduce prediction stability

Domain-agnostic: works on any domain.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TemporalSignal:
    """Single temporal adjustment"""
    category: str  # "information_decay", "early_stage", "volatility", etc.
    adjustment: float  # -0.20 to +0.20
    signal: str  # Human-readable explanation
    source: str = "temporal"


class TemporalAdjuster:
    """Adjust predictions based on temporal factors"""

    def adjust(self, raw_data: Dict[str, Any], context: Dict[str, Any]) -> List[TemporalSignal]:
        """
        Apply temporal adjustments for information age and lifecycle stage.

        Returns list of TemporalSignal objects.
        """
        signals = []

        # Check 1: Information decay
        decay = self._detect_information_decay(context)
        if decay:
            signals.append(decay)

        # Check 2: Decision lifecycle stage
        lifecycle = self._detect_lifecycle_stage(context)
        if lifecycle:
            signals.append(lifecycle)

        # Check 3: Market volatility
        volatility = self._detect_volatility(context)
        if volatility:
            signals.append(volatility)

        return signals

    def _detect_information_decay(self, context: Dict) -> TemporalSignal | None:
        """
        Detect information decay: How old is the data?

        Universal pattern: Information becomes stale predictably.
        - HR: Resume from 5 years ago ≠ current candidate
        - M&A: Market data from 3 months ago may be outdated
        - Law: Precedent ages; older cases less relevant
        - Real Estate: Comps from 6+ months ago questionable
        """
        data_age_days = context.get("data_age_days", 0)

        if data_age_days > 30:
            # Exponential decay: starts slow, accelerates
            # At 30 days: -5% decay
            # At 90 days: -12% decay
            # At 180 days: -15% decay (max)
            decay_fraction = min(data_age_days / 200, 0.15)  # Cap at 15%
            adjustment = -decay_fraction

            return TemporalSignal(
                category="information_decay",
                adjustment=adjustment,
                signal=f"Data is {data_age_days} days old; information decay reduces confidence by {abs(adjustment):.0%}"
            )

        return None

    def _detect_lifecycle_stage(self, context: Dict) -> TemporalSignal | None:
        """
        Detect lifecycle stage uncertainty.

        Universal pattern: Early stages have high uncertainty, late stages validate/invalidate.

        Stages (universal):
        - early_investigation: Just starting, lots unknown (-10%)
        - advanced_diligence: Got some data, better insight (-5%)
        - closing: Near-certain, validating (0%)
        - post_close: Outcome known, can validate prediction (+5% if correct, -5% if wrong)
        """
        stage = context.get("stage", "investigation")

        if stage == "early_investigation":
            return TemporalSignal(
                category="early_stage",
                adjustment=-0.10,
                signal="Early investigation stage: high uncertainty, many unknowns"
            )
        elif stage == "advanced_diligence":
            return TemporalSignal(
                category="advanced_diligence",
                adjustment=-0.05,
                signal="Advanced diligence: better information, but still uncertainties"
            )
        elif stage == "post_close":
            # Check if outcome validates or invalidates
            performing = context.get("performing")
            if performing is True:
                adjustment = +0.05
                signal = "Post-close: performing as predicted, validates model"
            elif performing is False:
                adjustment = -0.05
                signal = "Post-close: underperforming, invalidates prediction"
            else:
                # Don't know yet
                return None

            return TemporalSignal(
                category="post_close_validation",
                adjustment=adjustment,
                signal=signal
            )

        return None

    def _detect_volatility(self, context: Dict) -> TemporalSignal | None:
        """
        Detect market/environment volatility.

        Universal pattern: Volatile conditions reduce prediction accuracy.

        Volatility indicators:
        - high_volatility: Market turmoil, uncertain environment
        - interest_rate_sensitive: Macro volatility affects target
        - regulatory_uncertainty: Legal/regulatory changes pending
        """
        if context.get("high_volatility"):
            return TemporalSignal(
                category="volatility",
                adjustment=-0.08,
                signal="High market/environment volatility: predictions less stable in turbulent conditions"
            )

        if context.get("interest_rate_sensitive") and context.get("rate_uncertainty"):
            return TemporalSignal(
                category="interest_rate_sensitivity",
                adjustment=-0.06,
                signal="Interest rate uncertainty: sensitive target, reduced forecast reliability"
            )

        if context.get("regulatory_uncertainty"):
            return TemporalSignal(
                category="regulatory_risk",
                adjustment=-0.07,
                signal="Regulatory uncertainty pending: outcome may shift based on rules changes"
            )

        return None
