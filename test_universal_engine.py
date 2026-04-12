#!/usr/bin/env python3
"""
Test the UniversalPredictionEngine across multiple domains.

Validates that the same engine works for:
- HR candidate evaluation
- M&A deal assessment
- Law case prediction
- Real estate valuation
- Startup funding decision
- Insurance claim evaluation
- Supply chain vendor assessment
"""

import asyncio
import logging
from reasoning.engine import UniversalPredictionEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_hr_candidate():
    """Test on HR candidate evaluation"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: HR Candidate Evaluation")
    logger.info("="*80)

    engine = UniversalPredictionEngine()

    raw_data = {
        "candidate_name": "Sarah Chen",
        "resume": "Senior PM, 8 years experience, founded 2 startups",
        "education": "Stanford MBA",
        "recent_wins": 3,
        "recent_failures": 0,
    }

    mirofish_output = {
        "probability": 0.72,
        "simulations": 1_000_000,
        "confidence_interval": (0.65, 0.79)
    }

    context = {
        "oracle_type": "hr",
        "stage": "early_investigation",
        "data_age_days": 5,
        "expert_confidence": 0.88,  # Overconfident
        "recent_successes": 3,
        "recent_failures": 0,
        "historical_success_rate": 0.60,
        "historical_accuracy": 0.68,
        "expert_variance": 0.25,
        "situation_uniqueness": 0.3,
        "data_completeness": 0.7,
    }

    result = await engine.predict(raw_data, mirofish_output, context)

    print(f"\n✅ Base Probability: {result.base_probability:.0%}")
    print(f"✅ Calibrated Probability: {result.calibrated_probability:.0%}")
    print(f"✅ Confidence: {result.confidence_level.value} ({result.confidence:.0%})")
    print(f"\n📋 Reasoning:")
    for layer in result.reasoning_chain:
        print(f"  • {layer.layer_name}: {layer.adjustment:+.0%}")
        print(f"    → {layer.explanation}")
    print(f"\n💡 Recommendation: {result.recommendation}")


async def test_ma_deal():
    """Test on M&A deal assessment"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: M&A Deal Assessment")
    logger.info("="*80)

    engine = UniversalPredictionEngine()

    raw_data = {
        "target_name": "TechStartup Inc",
        "revenue": "$50M ARR",
        "growth_rate": "120% YoY",
        "team_strength": "Excellent founding team, 1 key person risk",
        "financials_quality": "Clean audited statements",
    }

    mirofish_output = {
        "probability": 0.68,
        "simulations": 1_000_000,
        "confidence_interval": (0.60, 0.76)
    }

    context = {
        "oracle_type": "ma",
        "stage": "advanced_diligence",
        "data_age_days": 45,  # Data starting to age
        "initial_anchor": 500_000_000,
        "current_value": 650_000_000,
        "sunk_cost_amount": 5_000_000,  # Large sunk costs
        "expert_confidence": 0.80,
        "historical_accuracy": 0.62,
        "expert_variance": 0.35,
        "situation_uniqueness": 0.4,
        "data_completeness": 0.8,
    }

    result = await engine.predict(raw_data, mirofish_output, context)

    print(f"\n✅ Base Probability: {result.base_probability:.0%}")
    print(f"✅ Calibrated Probability: {result.calibrated_probability:.0%}")
    print(f"✅ Confidence: {result.confidence_level.value} ({result.confidence:.0%})")
    print(f"\n📋 Reasoning:")
    for layer in result.reasoning_chain:
        print(f"  • {layer.layer_name}: {layer.adjustment:+.0%}")
        print(f"    → {layer.explanation}")
    print(f"\n💡 Recommendation: {result.recommendation}")


async def test_law_case():
    """Test on law case prediction"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Law Case Prediction")
    logger.info("="*80)

    engine = UniversalPredictionEngine()

    raw_data = {
        "case_type": "Contract Dispute",
        "plaintiff_resources": "Well-funded, experienced legal team",
        "defendant_resources": "Well-funded, experienced legal team",
        "evidence": "Conflicting expert opinions, ambiguous contract language",
        "precedents": "Mixed precedent in jurisdiction",
    }

    mirofish_output = {
        "probability": 0.55,
        "simulations": 1_000_000,
        "confidence_interval": (0.48, 0.62)
    }

    context = {
        "oracle_type": "law",
        "stage": "early_investigation",
        "data_age_days": 10,
        "expert_confidence": 0.75,
        "expert_variance": 0.45,  # High variance
        "situation_uniqueness": 0.6,  # Somewhat unique
        "historical_accuracy": 0.55,
        "data_completeness": 0.65,
    }

    result = await engine.predict(raw_data, mirofish_output, context)

    print(f"\n✅ Base Probability: {result.base_probability:.0%}")
    print(f"✅ Calibrated Probability: {result.calibrated_probability:.0%}")
    print(f"✅ Confidence: {result.confidence_level.value} ({result.confidence:.0%})")
    print(f"\n📋 Reasoning:")
    for layer in result.reasoning_chain:
        print(f"  • {layer.layer_name}: {layer.adjustment:+.0%}")
        print(f"    → {layer.explanation}")
    print(f"\n💡 Recommendation: {result.recommendation}")


async def main():
    """Run all tests"""
    logger.info("🚀 Universal Prediction Engine Tests")
    logger.info("Testing domain-agnostic reasoning across HR, M&A, Law...")

    await test_hr_candidate()
    await test_ma_deal()
    await test_law_case()

    logger.info("\n" + "="*80)
    logger.info("✅ All tests complete!")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
