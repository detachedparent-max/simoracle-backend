#!/usr/bin/env python3
"""
Test calibration monitoring - verify confidence matches accuracy.

Simulates making predictions and recording outcomes.
Shows how Expected Calibration Error (ECE) detects miscalibration.
"""

import asyncio
from reasoning.engine import UniversalPredictionEngine

async def test_calibration_monitoring():
    """Test that calibration monitor tracks accuracy vs confidence"""

    print("\n" + "="*80)
    print("TEST: Calibration Monitoring")
    print("="*80)

    engine = UniversalPredictionEngine()

    # Simulate 20 predictions with outcomes
    # Scenario: High confidence but low accuracy = overconfident
    test_cases = [
        # (confidence, was_correct) - overconfident scenario
        (0.85, True),   # ✓ right
        (0.85, False),  # ✗ wrong (overconfident!)
        (0.85, False),  # ✗ wrong (overconfident!)
        (0.80, True),   # ✓ right
        (0.80, False),  # ✗ wrong
        (0.75, True),   # ✓ right
        (0.75, False),  # ✗ wrong
        (0.70, True),   # ✓ right
        (0.70, True),   # ✓ right
        (0.65, False),  # ✗ wrong
        (0.65, True),   # ✓ right
        (0.60, True),   # ✓ right
        (0.60, True),   # ✓ right
        (0.55, False),  # ✗ wrong
        (0.55, True),   # ✓ right
        (0.50, True),   # ✓ right
        (0.50, False),  # ✗ wrong
        (0.45, False),  # ✗ wrong
        (0.45, True),   # ✓ right
        (0.40, True),   # ✓ right
    ]

    print(f"\nRecording {len(test_cases)} predictions...")
    for i, (conf, correct) in enumerate(test_cases):
        engine.record_outcome(confidence=conf, was_correct=correct)
        status = "✓" if correct else "✗"
        print(f"  {i+1:2d}. Confidence {conf:.0%} → {status}")

    # Analyze calibration
    print("\n" + "-"*80)
    print("CALIBRATION ANALYSIS")
    print("-"*80)

    stats = engine.get_calibration_stats()
    ece = engine.get_calibration_error()

    print(f"\nTotal predictions: {stats['n_predictions']}")
    print(f"Mean confidence: {stats['mean_confidence']:.0%}")
    print(f"Mean accuracy: {stats['mean_accuracy']:.0%}")
    print(f"Confidence std: {stats['confidence_std']:.3f}")
    print(f"Accuracy std: {stats['accuracy_std']:.3f}")
    print(f"\nExpected Calibration Error (ECE): {ece:.3f}")
    print(f"Overconfidence gap: {stats['overconfidence_gap']:+.0%}")
    print(f"Is overconfident: {stats['is_overconfident']}")
    print(f"Is underconfident: {stats['is_underconfident']}")

    # Interpretation
    print("\n" + "-"*80)
    print("INTERPRETATION")
    print("-"*80)

    if ece > 0.20:
        print(f"⚠️  MISCALIBRATED: ECE={ece:.3f} > 0.20")
        print(f"   Engine's confidence estimates don't match actual accuracy.")
    elif ece > 0.15:
        print(f"⚠️  BORDERLINE: ECE={ece:.3f} (acceptable < 0.15)")
        print(f"   Some calibration drift detected.")
    else:
        print(f"✅ WELL CALIBRATED: ECE={ece:.3f} < 0.15")
        print(f"   Confidence estimates match accuracy well.")

    if stats['is_overconfident']:
        print(f"   Problem: Engine too CONFIDENT")
        print(f"   → Predicts {stats['mean_confidence']:.0%} but only correct {stats['mean_accuracy']:.0%}")
        print(f"   → Recommendation: Lower confidence estimates or improve predictions")
    elif stats['is_underconfident']:
        print(f"   Problem: Engine too CONSERVATIVE")
        print(f"   → Predicts {stats['mean_confidence']:.0%} but actually correct {stats['mean_accuracy']:.0%}")
        print(f"   → Recommendation: Raise confidence estimates")
    else:
        print(f"   Good: Confidence matches accuracy")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_calibration_monitoring())
