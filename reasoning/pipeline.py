"""
Prediction Pipeline

Unified pipeline that combines MiroFish simulation with Universal Engine reasoning.
Supports streaming partial results, early-exit, and dynamic agent escalation.

Usage:
    pipeline = PredictionPipeline()

    result = await pipeline.predict(
        question="Will the temperature exceed 90°F in Austin tomorrow?",
        domain="weather",
        customer_data={"city": "Austin", "date": "2024-07-15"},
        context={"data_age_days": 0}
    )
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional, Any
from enum import Enum

from .engine import UniversalPredictionEngine
from .schemas import ReasoningOutput, ConfidenceLevel, LayerExplanation

logger = logging.getLogger(__name__)


class MiroFishBaseURL:
    DEFAULT = "http://localhost:5001"


@dataclass
class PartialMiroFishResult:
    """Partial result from MiroFish during simulation"""

    probability: float
    confidence: float
    agents_run: int
    rounds_completed: int
    is_still_running: bool
    early_signals: List[str] = field(default_factory=list)


@dataclass
class FullMiroFishResult:
    """Complete MiroFish simulation result"""

    probability: float
    confidence: float
    agents_run: int
    rounds_completed: int
    narrative: str
    simulation_id: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EarlySignal:
    """Signal from Engine based on partial MiroFish results"""

    needs_escalation: bool
    needs_abort: bool
    confidence: float
    concerns: List[str]
    recommendation: str


@dataclass
class PipelineConfig:
    """Configuration for PredictionPipeline"""

    mirofish_url: str = MiroFishBaseURL.DEFAULT
    base_agents: int = 100_000
    max_agents: int = 2_000_000
    escalation_threshold: float = 0.15
    min_confidence_for_early_exit: float = 0.80
    stream_interval_seconds: float = 5.0
    enable_early_exit: bool = True
    enable_escalation: bool = True


class MiroFishStreamingClient:
    """
    MiroFish client with streaming support.

    Wraps the existing MiroFish API to support:
    - Streaming partial results during simulation
    - Dynamic agent escalation mid-simulation
    - Early abort
    """

    def __init__(self, base_url: str = MiroFishBaseURL.DEFAULT):
        self.base_url = base_url
        self._simulation_active = False
        self._current_simulation_id: Optional[str] = None
        self._partial_results: List[Dict] = []
        self._poll_task: Optional[asyncio.Task] = None

    async def health_check(self) -> bool:
        """Check if MiroFish is available"""
        import requests

        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    async def start_simulation(
        self, question: str, domain: str, agents: int = 100_000, max_rounds: int = 30
    ) -> str:
        """
        Start a MiroFish simulation.

        Returns simulation_id for polling.
        """
        import requests

        self._simulation_active = True
        self._partial_results = []

        try:
            files = [("files", ("question.txt", question, "text/plain"))]
            data = {
                "project_name": f"pipeline_{domain}_{int(time.time())}",
                "simulation_requirement": f"Analyze and predict: {question}",
                "additional_context": f"Domain: {domain}",
                "max_agents": str(agents),
                "max_rounds": str(max_rounds),
            }

            resp = requests.post(
                f"{self.base_url}/api/graph/ontology/generate",
                files=files,
                data=data,
                timeout=120,
            )

            if resp.status_code != 200:
                raise Exception(f"Failed to start simulation: {resp.text}")

            result = resp.json()
            if result.get("success"):
                self._current_simulation_id = result["data"]["project_id"]
                return self._current_simulation_id

            raise Exception(f"Simulation start failed: {result.get('error')}")

        except Exception as e:
            self._simulation_active = False
            raise

    async def stream_results(
        self, simulation_id: str, interval: float = 5.0
    ) -> AsyncIterator[PartialMiroFishResult]:
        """
        Stream partial results from an active simulation.

        Yields PartialMiroFishResult as results become available.
        """
        import requests

        while self._simulation_active:
            try:
                resp = requests.get(
                    f"{self.base_url}/api/graph/project/{simulation_id}", timeout=10
                )

                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("success"):
                        data = result.get("data", {})
                        status = data.get("status", "")

                        partial = PartialMiroFishResult(
                            probability=data.get("probability", 0.5),
                            confidence=data.get("confidence", 0.5),
                            agents_run=data.get("agents_completed", 0),
                            rounds_completed=data.get("rounds_completed", 0),
                            is_still_running=status
                            not in ["completed", "failed", "error"],
                            early_signals=self._extract_early_signals(data),
                        )

                        yield partial

                        if not partial.is_still_running:
                            break

                await asyncio.sleep(interval)

            except Exception as e:
                logger.warning(f"Stream polling error: {e}")
                await asyncio.sleep(interval)

    async def escalate_agents(self, simulation_id: str, additional_agents: int) -> str:
        """
        Add more agents to running simulation.

        Returns updated simulation_id.
        """
        import requests

        try:
            resp = requests.post(
                f"{self.base_url}/api/simulation/{simulation_id}/escalate",
                json={"additional_agents": additional_agents},
                timeout=30,
            )

            if resp.status_code == 200:
                logger.info(
                    f"Escalated simulation {simulation_id} with {additional_agents} more agents"
                )
                return simulation_id

            logger.warning(
                f"Escalation failed, continuing with current agents: {resp.text}"
            )
            return simulation_id

        except Exception as e:
            logger.warning(f"Escalation error: {e}")
            return simulation_id

    async def abort_simulation(self, simulation_id: str):
        """Abort running simulation"""
        import requests

        self._simulation_active = False

        try:
            requests.post(
                f"{self.base_url}/api/simulation/{simulation_id}/abort", timeout=10
            )
        except Exception:
            pass

    async def get_final_result(
        self, simulation_id: str, timeout: float = 600.0
    ) -> FullMiroFishResult:
        """Wait for simulation to complete and return final result"""
        import requests

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                resp = requests.get(
                    f"{self.base_url}/api/graph/project/{simulation_id}", timeout=10
                )

                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("success"):
                        data = result.get("data", {})
                        status = data.get("status", "")

                        if status in ["completed", "done"]:
                            return FullMiroFishResult(
                                probability=data.get("probability", 0.5),
                                confidence=data.get("confidence", 0.5),
                                agents_run=data.get("agents_completed", 0),
                                rounds_completed=data.get("rounds_completed", 0),
                                narrative=data.get("narrative", ""),
                                simulation_id=simulation_id,
                                duration_seconds=time.time() - start_time,
                            )

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Final result polling error: {e}")
                await asyncio.sleep(5)

        raise TimeoutError(
            f"Simulation {simulation_id} did not complete within {timeout}s"
        )

    def _extract_early_signals(self, data: Dict) -> List[str]:
        """Extract early warning signals from partial data"""
        signals = []

        if data.get("divergence", 0) > 0.2:
            signals.append("HIGH_DIVERGENCE")

        if data.get("uncertainty", 0) > 0.4:
            signals.append("HIGH_UNCERTAINTY")

        if data.get("rounds_without_progress", 0) > 3:
            signals.append("CONVERGENCE_STALL")

        return signals

    def stop_streaming(self):
        """Stop streaming results"""
        self._simulation_active = False
        if self._poll_task:
            self._poll_task.cancel()


class PredictionPipeline:
    """
    Unified prediction pipeline combining MiroFish + Universal Engine.

    Features:
    - Streaming partial results to Engine for early reasoning
    - Dynamic agent escalation based on Engine feedback
    - Early exit when confidence is high enough
    - Full reasoning pass on final results
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.mirofish = MiroFishStreamingClient(self.config.mirofish_url)
        self.engine = UniversalPredictionEngine()

        logger.info(
            f"PredictionPipeline initialized (MiroFish: {self.config.mirofish_url})"
        )

    async def predict(
        self,
        question: str,
        domain: str,
        customer_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningOutput:
        """
        Run unified prediction pipeline.

        Args:
            question: Natural language question or prediction target
            domain: Domain type (weather, politics, hr, etc.)
            customer_data: Customer's input data
            context: Optional context (data_age_days, etc.)

        Returns:
            ReasoningOutput with calibrated probability + reasoning
        """
        context = context or {}
        context["domain"] = domain
        context["question"] = question

        logger.info(f"Starting pipeline: {domain} | Q: {question[:50]}...")

        try:
            simulation_id = await self.mirofish.start_simulation(
                question=question, domain=domain, agents=self.config.base_agents
            )

            escalation_count = 0
            async for partial in self.mirofish.stream_results(
                simulation_id, interval=self.config.stream_interval_seconds
            ):
                early_signal = await self._check_early_signal(
                    partial, customer_data, context
                )

                if early_signal.needs_abort:
                    logger.warning(f"Early abort: {early_signal.recommendation}")
                    await self.mirofish.abort_simulation(simulation_id)
                    break

                if early_signal.needs_escalation and escalation_count < 3:
                    escalation_count += 1
                    additional = self.config.base_agents * escalation_count
                    new_id = await self.mirofish.escalate_agents(
                        simulation_id, additional
                    )
                    logger.info(f"Escalated to {additional:,} more agents")
                    simulation_id = new_id

                if self.config.enable_early_exit:
                    if (
                        early_signal.confidence
                        >= self.config.min_confidence_for_early_exit
                    ):
                        logger.info(
                            f"Early exit: confidence {early_signal.confidence:.0%} sufficient"
                        )
                        break

            mirofish_result = await self.mirofish.get_final_result(simulation_id)

            final_result = await self.engine.predict(
                raw_data={"question": question, "domain": domain, **customer_data},
                mirofish_output={
                    "probability": mirofish_result.probability,
                    "confidence": mirofish_result.confidence,
                    "agents_run": mirofish_result.agents_run,
                    "rounds": mirofish_result.rounds_completed,
                    "narrative": mirofish_result.narrative,
                },
                context=context,
            )

            logger.info(
                f"Pipeline complete: {mirofish_result.probability:.0%} → "
                f"{final_result.calibrated_probability:.0%} "
                f"(conf: {final_result.confidence:.0%})"
            )

            return final_result

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise

    async def _check_early_signal(
        self, partial: PartialMiroFishResult, customer_data: Dict, context: Dict
    ) -> EarlySignal:
        """
        Engine checks partial MiroFish results for early signals.

        Returns EarlySignal with escalation/abort recommendations.
        """
        concerns = []
        needs_escalation = False
        needs_abort = False

        if partial.agents_run < 10_000:
            return EarlySignal(
                needs_escalation=False,
                needs_abort=False,
                confidence=0.0,
                concerns=["SIMULATION_JUST_STARTED"],
                recommendation="Continue monitoring",
            )

        confidence = await self._estimate_confidence(partial, customer_data, context)

        if partial.confidence < 0.4:
            concerns.append("Low MiroFish confidence")
            if partial.agents_run >= self.config.base_agents:
                needs_escalation = True

        if "HIGH_UNCERTAINTY" in partial.early_signals:
            concerns.append("High uncertainty in simulation")
            needs_escalation = True

        if "CONVERGENCE_STALL" in partial.early_signals:
            concerns.append("Simulation convergence stalled")
            needs_escalation = True

        if partial.probability < 0.15 or partial.probability > 0.85:
            concerns.append("Extreme probability (rare event)")

        if "HIGH_DIVERGENCE" in partial.early_signals:
            concerns.append("High divergence between agents")
            needs_escalation = True

        if context.get("data_age_days", 0) > 14:
            concerns.append("Stale data - need more verification")
            needs_escalation = True

        recommendation = self._generate_recommendation(
            needs_escalation, needs_abort, concerns, confidence
        )

        return EarlySignal(
            needs_escalation=needs_escalation,
            needs_abort=needs_abort,
            confidence=confidence,
            concerns=concerns,
            recommendation=recommendation,
        )

    async def _estimate_confidence(
        self, partial: PartialMiroFishResult, customer_data: Dict, context: Dict
    ) -> float:
        """
        Estimate confidence based on partial MiroFish results.

        Quick heuristic before full Engine pass.
        """
        confidence = partial.confidence

        if partial.early_signals:
            signal_penalty = len(partial.early_signals) * 0.05
            confidence -= signal_penalty

        agents_factor = min(partial.agents_run / 500_000, 1.0) * 0.2
        confidence += agents_factor

        rounds_factor = min(partial.rounds_completed / 20, 1.0) * 0.1
        confidence += rounds_factor

        return max(0.0, min(1.0, confidence))

    def _generate_recommendation(
        self,
        needs_escalation: bool,
        needs_abort: bool,
        concerns: List[str],
        confidence: float,
    ) -> str:
        """Generate human-readable recommendation"""
        if needs_abort:
            return f"ABORT: {', '.join(concerns)}"

        if needs_escalation:
            return f"ESCALATE: {', '.join(concerns)}"

        if confidence >= 0.8:
            return "CONFIDENT: Early exit possible"

        return "MONITORING: Continue pipeline"


class MockMiroFishClient:
    """
    Mock MiroFish client for testing without running actual MiroFish.

    Simulates streaming partial results with realistic behavior.
    """

    def __init__(self):
        self._simulation_active = False

    async def health_check(self) -> bool:
        return True

    async def start_simulation(
        self, question: str, domain: str, agents: int = 100_000, max_rounds: int = 30
    ) -> str:
        self._simulation_active = True
        return f"mock_sim_{int(time.time())}"

    async def stream_results(
        self, simulation_id: str, interval: float = 0.5
    ) -> AsyncIterator[PartialMiroFishResult]:
        """Simulate streaming results"""
        import random

        probability = random.uniform(0.3, 0.7)

        for round_num in range(1, 6):
            if not self._simulation_active:
                break

            await asyncio.sleep(interval)

            agents_run = int(100_000 * (round_num / 5))
            conf = 0.4 + (round_num * 0.1)

            signals = []
            if round_num >= 4:
                signals.append("CONVERGENCE_STALL")

            yield PartialMiroFishResult(
                probability=probability,
                confidence=min(conf, 0.9),
                agents_run=agents_run,
                rounds_completed=round_num,
                is_still_running=round_num < 5,
                early_signals=signals,
            )

    async def escalate_agents(self, simulation_id: str, additional_agents: int) -> str:
        await asyncio.sleep(0.1)
        return simulation_id

    async def abort_simulation(self, simulation_id: str):
        self._simulation_active = False

    async def get_final_result(
        self, simulation_id: str, timeout: float = 10.0
    ) -> FullMiroFishResult:
        await asyncio.sleep(0.5)
        return FullMiroFishResult(
            probability=0.65,
            confidence=0.75,
            agents_run=100_000,
            rounds_completed=5,
            narrative="Mock simulation completed",
            simulation_id=simulation_id,
            duration_seconds=3.0,
        )

    def stop_streaming(self):
        self._simulation_active = False


class MockPredictionPipeline(PredictionPipeline):
    """PredictionPipeline with mock MiroFish for testing"""

    def __init__(self, config: Optional[PipelineConfig] = None):
        super().__init__(config)
        self.mirofish = MockMiroFishClient()
