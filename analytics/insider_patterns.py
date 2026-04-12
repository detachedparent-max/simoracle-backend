"""
Insider pattern recognition - detects unusual confidence patterns
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from config import INSIDER_CONFIDENCE_JUMP_PCT, INSIDER_SIGNAL_LOOKBACK_HOURS
from database.queries import PredictionQueries


@dataclass
class InsiderSignal:
    prediction_id: str
    signal_type: str  # 'confidence_jump', 'model_agreement', 'early_accuracy'
    confidence_change_pct: float
    old_confidence: int
    new_confidence: int
    model_agreement: int  # 0-100: % of models in agreement
    description: str
    strength: int  # 0-100
    timestamp: datetime


class InsiderPatterns:
    """Detects suspicious confidence patterns that may signal insider knowledge"""

    @staticmethod
    def analyze_confidence_jumps(prediction_id: str) -> Optional[InsiderSignal]:
        """
        Detect sudden confidence jumps (>30% change in 1 hour)
        These may indicate new information arriving
        """
        prediction = PredictionQueries.get_prediction_by_id(prediction_id)
        if not prediction:
            return None

        # Get reasoning history
        reasoning_logs = PredictionQueries.get_reasoning_for_prediction(prediction_id)
        if len(reasoning_logs) < 2:
            return None

        # Sort by timestamp
        sorted_logs = sorted(reasoning_logs, key=lambda x: x['timestamp'])

        # Check for confidence jumps within 1 hour
        for i in range(1, len(sorted_logs)):
            current_log = sorted_logs[i]
            previous_log = sorted_logs[i - 1]

            current_time = datetime.fromisoformat(current_log['timestamp'])
            previous_time = datetime.fromisoformat(previous_log['timestamp'])

            time_diff = (current_time - previous_time).total_seconds() / 3600  # hours

            if time_diff > 1:  # Skip if more than 1 hour apart
                continue

            # Get confidence from prediction at each time
            # (In real implementation, would track confidence per reasoning log)
            pred_confidence = prediction['confidence']

            # Estimate old/new based on reasoning quality
            old_confidence = InsiderPatterns._estimate_confidence(previous_log)
            new_confidence = InsiderPatterns._estimate_confidence(current_log)

            change_pct = ((new_confidence - old_confidence) / old_confidence * 100) if old_confidence > 0 else 0

            if abs(change_pct) >= INSIDER_CONFIDENCE_JUMP_PCT:
                return InsiderSignal(
                    prediction_id=prediction_id,
                    signal_type='confidence_jump',
                    confidence_change_pct=change_pct,
                    old_confidence=old_confidence,
                    new_confidence=new_confidence,
                    model_agreement=80,  # Placeholder
                    description=f"Confidence jump {change_pct:+.1f}% in 1 hour from {previous_log['model']} → {current_log['model']}",
                    strength=int(min(100, abs(change_pct) * 2)),
                    timestamp=current_time,
                )

        return None

    @staticmethod
    def analyze_model_agreement(prediction_id: str) -> Optional[InsiderSignal]:
        """
        Analyze multi-model consensus
        Strong agreement on unlikely predictions may signal insider info
        """
        reasoning_logs = PredictionQueries.get_reasoning_for_prediction(prediction_id)

        if len(reasoning_logs) < 2:
            return None

        # Count models
        models = {}
        for log in reasoning_logs:
            model = log['model']
            consensus = log.get('consensus_status', 'unknown')
            models[model] = consensus

        # Check if all models agree
        if len(set(models.values())) == 1:
            agreement = 100
            consensus_status = models[list(models.keys())[0]]

            if consensus_status == 'strong':
                strength = 85
            elif consensus_status == 'moderate':
                strength = 50
            else:
                strength = 30

            return InsiderSignal(
                prediction_id=prediction_id,
                signal_type='model_agreement',
                confidence_change_pct=0,
                old_confidence=0,
                new_confidence=0,
                model_agreement=agreement,
                description=f"{len(models)} models show {consensus_status} agreement",
                strength=strength,
                timestamp=datetime.now(),
            )

        return None

    @staticmethod
    def detect_early_accuracy(prediction_id: str, recent_accuracy_pct: float) -> Optional[InsiderSignal]:
        """
        Detect patterns where early confidence predicts eventual accuracy
        High early confidence + high eventual accuracy may indicate edge
        """
        prediction = PredictionQueries.get_prediction_by_id(prediction_id)

        if not prediction or prediction['outcome'] is None:
            return None  # Only for resolved predictions

        early_confidence = prediction['confidence']

        if early_confidence >= 75 and recent_accuracy_pct >= 70:
            return InsiderSignal(
                prediction_id=prediction_id,
                signal_type='early_accuracy',
                confidence_change_pct=0,
                old_confidence=early_confidence,
                new_confidence=early_confidence,
                model_agreement=int(recent_accuracy_pct),
                description=f"High early confidence ({early_confidence}) predicted correctly",
                strength=int(min(100, (early_confidence + recent_accuracy_pct) / 2)),
                timestamp=datetime.now(),
            )

        return None

    @staticmethod
    def _estimate_confidence(reasoning_log: Dict[str, Any]) -> int:
        """Estimate confidence from a reasoning log"""
        # In a real system, would extract from confidence_driver field
        confidence_driver = reasoning_log.get('confidence_driver', '')

        if 'very high' in confidence_driver.lower() or 'certain' in confidence_driver.lower():
            return 9
        elif 'high' in confidence_driver.lower():
            return 7
        elif 'moderate' in confidence_driver.lower():
            return 5
        elif 'low' in confidence_driver.lower():
            return 3
        else:
            return 5  # Default

    @staticmethod
    def scan_all_recent_predictions() -> List[InsiderSignal]:
        """Scan all recent predictions for insider patterns"""
        signals = []

        # Get predictions from last INSIDER_SIGNAL_LOOKBACK_HOURS
        predictions = PredictionQueries.get_predictions(limit=100)

        for prediction in predictions:
            # Check confidence jumps
            jump_signal = InsiderPatterns.analyze_confidence_jumps(prediction['id'])
            if jump_signal:
                signals.append(jump_signal)

            # Check model agreement
            agreement_signal = InsiderPatterns.analyze_model_agreement(prediction['id'])
            if agreement_signal:
                signals.append(agreement_signal)

        return signals

    @staticmethod
    def format_signals(signals: List[InsiderSignal]) -> List[Dict[str, Any]]:
        """Format signals for API response"""
        return [
            {
                'prediction_id': signal.prediction_id,
                'signal_type': signal.signal_type,
                'confidence_change_pct': round(signal.confidence_change_pct, 2),
                'old_confidence': signal.old_confidence,
                'new_confidence': signal.new_confidence,
                'model_agreement': signal.model_agreement,
                'description': signal.description,
                'strength': signal.strength,
                'timestamp': signal.timestamp.isoformat(),
            }
            for signal in signals
        ]
