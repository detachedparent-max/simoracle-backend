"""
OracleProvider interface - abstract base for any probability source.

Any system that produces probabilities can implement this interface:
- MiroFish (1M agent simulations)
- LLM-based forecasting
- Statistical models
- Customer proprietary models
- Hybrid approaches

Internal module - for advanced customers only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, AsyncIterator


@dataclass
class OracleResult:
    """Standard output from any oracle provider"""

    probability: float                          # Final probability (0-1)
    narrative: str                              # Explanation/reasoning
    supporting_data: Dict[str, Any] = field(default_factory=dict)  # Oracle-specific details
    metadata: Dict[str, Any] = field(default_factory=dict)  # Trace logs, timestamps, etc.


class OracleProvider(ABC):
    """
    Abstract oracle provider.

    Implement this interface to plug in any probability source into UniversalPredictionEngine.

    Example (bring your own model):
        class MyCustomOracle(OracleProvider):
            async def get_probability(self, question, domain, context):
                # Call your proprietary model
                prob = await my_model.predict(question)
                return OracleResult(
                    probability=prob,
                    narrative="Based on custom model v2",
                    supporting_data={"model": "custom_v2"}
                )

        engine = UniversalPredictionEngine(oracle_provider=MyCustomOracle())
    """

    @abstractmethod
    async def get_probability(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> OracleResult:
        """
        Generate a probability for a prediction question.

        Args:
            question: The prediction question (e.g., "Will X happen?")
            domain: Domain type (weather, hr, mna, geopolitics, etc.)
            context: Optional context (data_age_days, expert_opinion, etc.)

        Returns:
            OracleResult with probability, narrative, and metadata

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If probability generation fails
        """
        pass

    async def stream_probabilities(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[OracleResult]:
        """
        Optional: Stream partial probabilities as they're computed.

        Useful for long-running oracles that want to report incremental progress.
        Default implementation: yields single final result.

        Args:
            question: The prediction question
            domain: Domain type
            context: Optional context

        Yields:
            OracleResult objects (may be partial during computation)

        Example (streaming oracle):
            async def stream_probabilities(self, question, domain, context):
                for agents_run in [10000, 50000, 100000, 1000000]:
                    partial = await self.compute_partial(question, agents_run)
                    yield OracleResult(
                        probability=partial.prob,
                        narrative=partial.explanation,
                        supporting_data={"agents_run": agents_run}
                    )
        """
        yield await self.get_probability(question, domain, context)
