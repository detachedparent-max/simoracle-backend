"""
Shared data structures for reasoning engine.
Used across all layers and API endpoints.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


# Enums


class OracleType(str, Enum):
    HR = "hr"
    MA = "ma"
    LAW = "law"
    REAL_ESTATE = "real_estate"
    STARTUP_FUNDING = "startup_funding"
    INSURANCE = "insurance"
    SUPPLY_CHAIN = "supply_chain"
    WEATHER = "weather"
    POLITICS = "politics"


class DecisionStage(str, Enum):
    EARLY_INVESTIGATION = "early_investigation"
    MID_DILIGENCE = "mid_diligence"
    FINAL_DECISION = "final_decision"
    POST_CLOSE = "post_close"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    GUARDED = "guarded"


# Pydantic Models (for FastAPI)


class ReasoningRequest(BaseModel):
    """Input to /api/v1/predictions/reason endpoint"""

    oracle_type: OracleType
    raw_data: Dict[str, Any]  # Customer's actual data
    mirofish_output: Dict[str, Any]  # From MiroFish: {"probability": 0.72, ...}
    domain_context: Optional[Dict[str, Any]] = None
    show_probability: bool = (
        False  # If True, show numeric prob. If False, blurred (customer-facing)
    )


class ReasoningResponse(BaseModel):
    """Output from /api/v1/predictions/reason endpoint"""

    base_probability: float
    calibrated_probability: Optional[float]  # Blurred if show_probability=False
    confidence: float
    reasoning_chain: List[Dict[str, Any]]
    recommendation: str
    caveats: List[str]
    timestamp: datetime


# Dataclass (for internal use)


@dataclass
class LayerExplanation:
    """What one reasoning layer discovered"""

    layer_name: str
    adjustment: float  # e.g., -0.15
    explanation: str  # Human-readable
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResultData:
    """Simplified validation result for output"""

    level: str
    message: str
    field: Optional[str] = None


@dataclass
class ReasoningOutput:
    """Complete output from ReasoningEngine"""

    base_probability: float
    calibrated_probability: float
    confidence: float
    confidence_level: ConfidenceLevel
    reasoning_chain: List[LayerExplanation]
    recommendation: str
    caveats: List[str]
    timestamp: datetime
    oracle_type: str
    data_summary: Dict[str, Any] = field(default_factory=dict)
    validation_level: str = "pass"
    validation_warnings: List[str] = field(default_factory=list)
    staleness_ceiling: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dict (full details)"""
        return {
            "base_probability": self.base_probability,
            "calibrated_probability": self.calibrated_probability,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "reasoning_chain": [
                {
                    "layer_name": layer.layer_name,
                    "adjustment": layer.adjustment,
                    "explanation": layer.explanation,
                    "details": layer.details,
                }
                for layer in self.reasoning_chain
            ],
            "recommendation": self.recommendation,
            "caveats": self.caveats,
            "timestamp": self.timestamp.isoformat(),
            "oracle_type": self.oracle_type,
            "validation_level": self.validation_level,
            "validation_warnings": self.validation_warnings,
            "staleness_ceiling": self.staleness_ceiling,
        }

    def to_customer_facing_dict(self) -> Dict:
        """
        Convert to dict for customer report.
        Intentionally blurs numeric probability.
        Shows ONLY reasoning and recommendation.
        """
        return {
            "predicted_outcome": "[BLURRED]",
            "confidence_level": self.confidence_level.value,
            "reasoning": [
                {
                    "factor": layer.layer_name.replace("_", " ").title(),
                    "signal": layer.explanation,
                    "impact": "Higher"
                    if layer.adjustment > 0
                    else "Lower"
                    if layer.adjustment < 0
                    else "Neutral",
                }
                for layer in self.reasoning_chain
            ],
            "recommendation": self.recommendation,
            "caveats": self.caveats,
            "confidence_note": self._confidence_note(),
            "timestamp": self.timestamp.isoformat(),
        }

    def _confidence_note(self) -> str:
        """Generate human-readable confidence statement"""
        if self.confidence_level == ConfidenceLevel.HIGH:
            return "High confidence: Data is complete and historical patterns align with prediction."
        elif self.confidence_level == ConfidenceLevel.MODERATE:
            return "Moderate confidence: Some data gaps or moderate pattern variance."
        elif self.confidence_level == ConfidenceLevel.GUARDED:
            return "Guarded confidence: Significant unknowns or conflicting signals."
        else:
            return "Low confidence: Limited data or high uncertainty."


@dataclass
class MiroFishOutput:
    """What MiroFish returns from simulation"""

    probability: float  # 0.0-1.0
    simulations: int  # Number of simulations run
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    seed_data: Optional[Dict[str, Any]] = None  # What was fed to MiroFish
    model_version: str = "mirofish-1.0"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HRPredictionData:
    """Structured HR data for prediction"""

    candidate_name: str
    candidate_background: Dict[str, Any]  # Resume, education, skills
    job_history: List[Dict[str, Any]]  # Previous roles
    role_requirements: Dict[str, Any]  # What job requires
    company_context: Dict[str, Any]  # Company size, stage, culture
    other_candidates: Optional[int] = None  # How many other candidates


@dataclass
class MAPredictionData:
    """Structured M&A data for prediction"""

    target_name: str
    target_financials: Dict[str, Any]  # Revenue, growth, margins
    target_team: Dict[str, Any]  # Management, key people
    acquirer_context: Dict[str, Any]  # Fund strategy, integration capability
    proposed_price: float
    estimated_synergies: Dict[str, Any]


@dataclass
class LawPredictionData:
    """Structured Law data for prediction"""

    case_id: str
    case_type: str  # Contract, IP, employment, tort, criminal
    parties: Dict[str, Any]  # Plaintiff resources, defendant resources
    judge_assigned: Optional[str] = None
    jurisdiction: Optional[str] = None
    evidence_strength: Optional[float] = None  # 0-1 percentile
    comparable_cases: Optional[List[Dict]] = None
    settlement_offers: Optional[List[float]] = None


@dataclass
class RealEstatePredictionData:
    """Structured Real Estate data for prediction"""

    property_address: str
    property_details: Dict[str, Any]  # Age, condition, zoning
    market_comps: List[Dict[str, Any]]  # Recent sales
    neighborhood_metrics: Dict[str, Any]  # Population, crime, schools
    proposed_price: float
    intended_use: str  # Flip, hold, develop, rent


@dataclass
class LayerAdjustment:
    """What a single layer contributes"""

    layer_name: str
    adjustment_amount: float
    reasoning: str
    confidence: float  # 0-1, how sure we are about this adjustment
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProbabilityBlendConfig:
    """Configuration for probability blending"""

    max_adjustment: float = 0.20  # No adjustment can exceed ±0.20
    decay_factor: float = 0.70  # Adjustments only move 70% toward their target
    min_probability: float = 0.01  # Never say 0% certain
    max_probability: float = 0.99  # Never say 100% certain
    use_harmonic_mean: bool = (
        True  # For confidence: harmonic (conservative) vs arithmetic
    )
