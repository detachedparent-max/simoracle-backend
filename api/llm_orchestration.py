"""
Multi-model LLM orchestration for SimOracle
Queries Claude, Gemini, and GPT-4 in parallel for consensus predictions
Uses OpenRouter as unified API endpoint for simplicity
"""
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """
    Coordinates multi-model prediction consensus
    - Routes to Claude (Sonnet 4), Gemini 2.0, GPT-4 Turbo via OpenRouter
    - Aggregates confidence scores across models
    - Returns final probability with consensus strength
    """

    # OpenRouter model IDs (use latest versions)
    MODELS = {
        "claude": "anthropic/claude-3.5-sonnet",
        "gemini": "google/gemini-2.0-flash-exp",
        "gpt4": "openai/gpt-4-turbo",
    }

    OPENROUTER_API_BASE = "https://openrouter.io/api/v1"
    OPENROUTER_TIMEOUT = 30  # seconds

    def __init__(self, api_key: str):
        """
        Initialize with OpenRouter API key
        Args:
            api_key: OpenRouter API key from environment
        """
        self.api_key = api_key
        self.client = None

    async def get_client(self) -> httpx.AsyncClient:
        """Lazy-load async HTTP client"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.OPENROUTER_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://simoracle.com",
                    "X-Title": "SimOracle Prediction Engine",
                },
                timeout=self.OPENROUTER_TIMEOUT,
            )
        return self.client

    async def predict(
        self,
        event: str,
        oracle: str,
        deadline: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate prediction with multi-model consensus

        Args:
            event: Market event question (e.g., "Will Bitcoin close above $70k?")
            oracle: Oracle type (weather, politics, sports, crypto, macro)
            deadline: ISO timestamp for market resolution
            context: Optional background context

        Returns:
            {
                "prediction_id": "pred_xyz",
                "event": "...",
                "probability": 0.65,  # Final consensus probability
                "consensus": {
                    "models": [
                        {"model": "claude-opus-4-6", "probability": 0.68, "confidence": 8},
                        ...
                    ],
                    "agreement": "strong|moderate|weak",
                    "final_probability": 0.65
                },
                "reasoning": "...",
                "timestamp": "2026-04-04T10:30:00Z"
            }
        """
        try:
            # Query all 3 models in parallel
            tasks = [
                self._query_model("claude", event, oracle, deadline, context),
                self._query_model("gemini", event, oracle, deadline, context),
                self._query_model("gpt4", event, oracle, deadline, context),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle failures
            model_predictions = []
            for model_name, result in zip(["claude", "gemini", "gpt4"], results):
                if isinstance(result, Exception):
                    logger.warning(f"Model {model_name} failed: {result}")
                    continue
                model_predictions.append({
                    "model": model_name,
                    **result,
                })

            if not model_predictions:
                raise Exception("All models failed to generate predictions")

            # Aggregate consensus
            consensus = self._aggregate_consensus(model_predictions, event)

            prediction_id = f"pred_{datetime.utcnow().isoformat().replace(':', '').split('.')[0]}"

            return {
                "prediction_id": prediction_id,
                "event": event,
                "oracle": oracle,
                "probability": consensus["final_probability"],
                "consensus": {
                    "models": model_predictions,
                    "agreement": consensus["agreement"],
                    "final_probability": consensus["final_probability"],
                },
                "reasoning": consensus["reasoning"],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            logger.error(f"Multi-model prediction failed: {e}")
            raise

    async def _query_model(
        self,
        model_name: str,
        event: str,
        oracle: str,
        deadline: Optional[str],
        context: Optional[str],
    ) -> Dict[str, Any]:
        """Query a single model for prediction"""
        try:
            client = await self.get_client()

            prompt = self._build_prompt(event, oracle, deadline, context, model_name)

            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.MODELS[model_name],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,  # Lower temp for more consistent predictions
                    "max_tokens": 1000,
                },
            )

            response.raise_for_status()
            data = response.json()

            # Extract prediction and confidence from response
            message = data["choices"][0]["message"]["content"]
            parsed = self._parse_prediction_response(message)

            return {
                "probability": parsed["probability"],
                "confidence": parsed["confidence"],
                "reasoning_snippet": parsed["reasoning"],
            }

        except Exception as e:
            logger.error(f"Model query failed for {model_name}: {e}")
            raise

    def _build_prompt(
        self,
        event: str,
        oracle: str,
        deadline: Optional[str],
        context: Optional[str],
        model_name: str,
    ) -> str:
        """Build structured prompt for LLM prediction"""
        deadline_str = f"Market resolves: {deadline}" if deadline else ""
        context_str = f"Context: {context}" if context else ""

        return f"""You are SimOracle, an institutional prediction engine. Generate a probability estimate for this market event.

EVENT: {event}
ORACLE TYPE: {oracle}
{deadline_str}
{context_str}

Respond in JSON format with ONLY these fields (no markdown):
{{
    "probability": <float 0.0-1.0>,
    "confidence": <int 1-10>,
    "reasoning": "<brief causal explanation (1-2 sentences)>"
}}

Output valid JSON only."""

    def _parse_prediction_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON prediction response from model"""
        try:
            # Try to extract JSON from response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start:end]
            parsed = json.loads(json_str)

            return {
                "probability": float(parsed.get("probability", 0.5)),
                "confidence": int(parsed.get("confidence", 5)),
                "reasoning": parsed.get("reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Failed to parse prediction response: {e}")
            return {
                "probability": 0.5,
                "confidence": 3,
                "reasoning": "Response parsing failed",
            }

    def _aggregate_consensus(
        self,
        model_predictions: List[Dict[str, Any]],
        event: str,
    ) -> Dict[str, Any]:
        """
        Aggregate predictions across models
        Calculate final probability and agreement strength
        """
        probabilities = [p["probability"] for p in model_predictions]
        confidences = [p["confidence"] for p in model_predictions]

        final_probability = sum(probabilities) / len(probabilities)
        avg_confidence = sum(confidences) / len(confidences)

        # Calculate agreement strength (standard deviation of probabilities)
        variance = sum((p - final_probability) ** 2 for p in probabilities) / len(probabilities)
        std_dev = variance ** 0.5

        # Interpret agreement level
        if std_dev < 0.05:
            agreement = "strong"
        elif std_dev < 0.12:
            agreement = "moderate"
        else:
            agreement = "weak"

        # Combine reasoning from all models
        reasoning_snippets = [
            p.get("reasoning_snippet", "") for p in model_predictions
        ]
        combined_reasoning = " | ".join(
            [r for r in reasoning_snippets if r][:3]
        )  # Top 3 reasons

        return {
            "final_probability": final_probability,
            "agreement": agreement,
            "reasoning": combined_reasoning,
        }

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()


async def get_llm_orchestrator(api_key: str) -> LLMOrchestrator:
    """Factory function to get orchestrator instance"""
    return LLMOrchestrator(api_key)
