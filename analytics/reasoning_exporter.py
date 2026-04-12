"""
Reasoning/audit trail exporter - outputs causal chains in JSON/CSV
"""
import json
import csv
from io import StringIO
from typing import Dict, Any, List, Optional
from datetime import datetime
from database.queries import PredictionQueries, ReasoningQueries


class ReasoningExporter:
    """Exports prediction reasoning and audit trails for compliance"""

    @staticmethod
    def export_prediction_reasoning_json(prediction_id: str) -> Dict[str, Any]:
        """Export full reasoning for one prediction as JSON"""
        prediction = PredictionQueries.get_prediction_by_id(prediction_id)
        if not prediction:
            return {}

        reasoning_logs = ReasoningQueries.get_reasoning_for_prediction(prediction_id)

        # Build causal chain
        causal_chain = []
        for log in reasoning_logs:
            chain_item = {
                'sequence': len(causal_chain) + 1,
                'model': log['model'],
                'timestamp': log['timestamp'],
                'catalyst_primary': log['catalyst_primary'],
                'catalyst_secondary': log.get('catalyst_secondary'),
                'confidence_driver': log.get('confidence_driver'),
                'consensus_status': log.get('consensus_status'),
                'data_sources': json.loads(log['data_sources']) if log['data_sources'] else [],
            }
            causal_chain.append(chain_item)

        return {
            'prediction_id': prediction_id,
            'event': prediction['event'],
            'oracle': prediction['oracle'],
            'probability': prediction['probability'],
            'action': prediction['action'],
            'confidence': prediction['confidence'],
            'market_id': prediction.get('market_id'),
            'platform': prediction.get('platform'),
            'created_at': prediction['timestamp'],
            'outcome': prediction.get('outcome'),
            'outcome_timestamp': prediction.get('outcome_timestamp'),
            'causal_chain': causal_chain,
            'model_consensus': ReasoningExporter._compute_consensus(reasoning_logs),
            'reasoning_summary': ReasoningExporter._generate_summary(reasoning_logs),
        }

    @staticmethod
    def export_predictions_json(
        oracle: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Export multiple predictions as JSON"""
        predictions = PredictionQueries.get_predictions(oracle=oracle, limit=limit)

        exported = []
        for pred in predictions:
            exported.append(ReasoningExporter.export_prediction_reasoning_json(pred['id']))

        return {
            'export_timestamp': datetime.now().isoformat(),
            'total_predictions': len(exported),
            'oracle_filter': oracle,
            'predictions': exported,
        }

    @staticmethod
    def export_to_csv(
        oracle: Optional[str] = None,
        limit: int = 100,
    ) -> str:
        """Export predictions as CSV with reasoning columns"""
        predictions = PredictionQueries.get_predictions(oracle=oracle, limit=limit)

        output = StringIO()
        fieldnames = [
            'prediction_id',
            'oracle',
            'event',
            'probability',
            'action',
            'confidence',
            'created_at',
            'outcome',
            'primary_catalyst',
            'secondary_catalyst',
            'confidence_driver',
            'models_used',
            'model_consensus',
            'data_sources_count',
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for pred in predictions:
            reasoning_logs = ReasoningQueries.get_reasoning_for_prediction(pred['id'])

            primary_catalysts = [log.get('catalyst_primary', '') for log in reasoning_logs]
            secondary_catalysts = [log.get('catalyst_secondary', '') for log in reasoning_logs if log.get('catalyst_secondary')]
            confidence_drivers = [log.get('confidence_driver', '') for log in reasoning_logs]
            models_used = [log['model'] for log in reasoning_logs]
            total_sources = sum(
                len(json.loads(log['data_sources']) if log['data_sources'] else [])
                for log in reasoning_logs
            )

            row = {
                'prediction_id': pred['id'],
                'oracle': pred['oracle'],
                'event': pred['event'],
                'probability': pred['probability'],
                'action': pred['action'],
                'confidence': pred['confidence'],
                'created_at': pred['timestamp'],
                'outcome': pred.get('outcome') or 'PENDING',
                'primary_catalyst': '; '.join(primary_catalysts),
                'secondary_catalyst': '; '.join(secondary_catalysts),
                'confidence_driver': '; '.join(confidence_drivers),
                'models_used': ', '.join(models_used),
                'model_consensus': ReasoningExporter._compute_consensus(reasoning_logs),
                'data_sources_count': total_sources,
            }
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def _compute_consensus(reasoning_logs: List[Dict[str, Any]]) -> str:
        """Determine model consensus level"""
        if not reasoning_logs:
            return 'unknown'

        statuses = [log.get('consensus_status', 'unknown') for log in reasoning_logs]

        strong_count = statuses.count('strong')
        moderate_count = statuses.count('moderate')
        total = len(statuses)

        if strong_count >= total * 0.7:
            return 'strong'
        elif moderate_count >= total * 0.5:
            return 'moderate'
        else:
            return 'weak'

    @staticmethod
    def _generate_summary(reasoning_logs: List[Dict[str, Any]]) -> str:
        """Generate natural language summary of reasoning"""
        if not reasoning_logs:
            return "No reasoning available"

        primary_catalysts = [
            log.get('catalyst_primary', '')
            for log in reasoning_logs
            if log.get('catalyst_primary')
        ]

        if not primary_catalysts:
            return "Reasoning based on model consensus"

        # Simple summary: concatenate primary catalysts
        summary = "Based on: " + "; ".join(primary_catalysts)
        return summary[:500]  # Truncate to 500 chars

    @staticmethod
    def generate_audit_trail(
        prediction_id: str,
        include_raw_reasoning: bool = False,
    ) -> Dict[str, Any]:
        """Generate compliance-ready audit trail"""
        prediction = PredictionQueries.get_prediction_by_id(prediction_id)
        reasoning_logs = ReasoningQueries.get_reasoning_for_prediction(prediction_id)

        if not prediction:
            return {}

        audit_trail = {
            'audit_metadata': {
                'export_timestamp': datetime.now().isoformat(),
                'prediction_id': prediction_id,
                'audit_level': 'full' if include_raw_reasoning else 'summary',
            },
            'prediction_details': {
                'event': prediction['event'],
                'oracle': prediction['oracle'],
                'probability': prediction['probability'],
                'action': prediction['action'],
                'confidence': prediction['confidence'],
                'created_at': prediction['timestamp'],
                'outcome': prediction.get('outcome'),
                'market_id': prediction.get('market_id'),
            },
            'causal_chain': [],
            'compliance_notes': [],
        }

        # Build detailed causal chain
        for i, log in enumerate(reasoning_logs, 1):
            chain_entry = {
                'step': i,
                'model': log['model'],
                'timestamp': log['timestamp'],
                'reasoning': {
                    'primary_catalyst': log['catalyst_primary'],
                    'secondary_catalyst': log.get('catalyst_secondary'),
                    'confidence_driver': log.get('confidence_driver'),
                }
            }

            if include_raw_reasoning:
                chain_entry['raw_reasoning'] = log.get('reasoning_text')
                chain_entry['data_sources'] = json.loads(log['data_sources']) if log['data_sources'] else []

            audit_trail['causal_chain'].append(chain_entry)

        # Add compliance notes
        if len(reasoning_logs) < 2:
            audit_trail['compliance_notes'].append("WARNING: Single model reasoning, no consensus verification")
        else:
            models = set(log['model'] for log in reasoning_logs)
            audit_trail['compliance_notes'].append(f"Consensus verified across {len(models)} models: {', '.join(models)}")

        if prediction.get('outcome'):
            audit_trail['compliance_notes'].append(f"Prediction resolved as: {prediction['outcome']}")

        return audit_trail
