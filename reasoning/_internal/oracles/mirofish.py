"""
MiroFish-backed oracle provider.

Implementation detail - customers use UniversalPredictionEngine, not this directly.

Wraps MiroFishStreamingClient to provide clean OracleProvider interface.
"""

import logging
from typing import Dict, Any, Optional, AsyncIterator

from .interface import OracleProvider, OracleResult
from .mirofish_client import MiroFishStreamingClient, PipelineConfig

logger = logging.getLogger(__name__)


class MiroFishOracle(OracleProvider):
    """
    MiroFish-backed oracle provider.

    Uses 1M agent simulations to generate probability distributions.
    This is an implementation detail - customers only interact through UniversalPredictionEngine.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Args:
            config: PipelineConfig for MiroFish simulation
                   (base_agents, stream_interval_seconds, seed, etc.)
                   If None, uses defaults.
        """
        self.client = MiroFishStreamingClient(config or PipelineConfig())
        self.config = config or PipelineConfig()

    async def get_probability(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> OracleResult:
        """
        Run full MiroFish simulation, return final probability.

        Args:
            question: Prediction question
            domain: Domain type (weather, hr, mna, etc.)
            context: Optional context (data_age_days, etc.)

        Returns:
            OracleResult with final probability and narrative
        """
        # Consume all streamed results, use final
        final_result = None
        async for result in self.stream_probabilities(question, domain, context):
            final_result = result

        if final_result is None:
            raise RuntimeError("MiroFish simulation produced no results")

        return final_result

    async def stream_probabilities(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[OracleResult]:
        """
        Stream partial probabilities as MiroFish simulation progresses.

        Yields OracleResult for each partial checkpoint as agents complete.

        Args:
            question: Prediction question
            domain: Domain type
            context: Optional context

        Yields:
            OracleResult with probability, narrative, agent count, etc.
        """
        try:
            async for partial in self.client.run_simulation(
                question=question,
                domain=domain,
                context=context,
            ):
                # Convert partial MiroFish result to standard OracleResult
                yield OracleResult(
                    probability=partial.probability,
                    narrative=partial.narrative or f"Simulating with {partial.agents_run:,} agents",
                    supporting_data={
                        "agents_run": partial.agents_run,
                        "rounds_completed": partial.rounds_completed,
                        "is_partial": True,
                    },
                    metadata={
                        "simulation_id": getattr(partial, "simulation_id", None),
                        "duration_seconds": getattr(partial, "duration_seconds", 0),
                        "timestamp": getattr(partial, "timestamp", None),
                    },
                )
        except Exception as e:
            logger.error(f"MiroFish simulation failed: {e}")
            raise RuntimeError(f"Oracle probability generation failed: {e}") from e
