"""
MiroFish Streaming Client

Implementation detail - handles subprocess management, streaming, escalation.
Internal module - customers should not import this directly.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional, Any

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
    narrative: Optional[str] = None
    simulation_id: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
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
class PipelineConfig:
    """Configuration for MiroFish simulation"""

    mirofish_url: str = MiroFishBaseURL.DEFAULT
    base_agents: int = 100_000
    max_agents: int = 2_000_000
    stream_interval_seconds: float = 5.0
    determinism_seed: Optional[int] = None


class MiroFishStreamingClient:
    """
    MiroFish client with streaming support.

    Wraps the existing MiroFish API to support:
    - Streaming partial results during simulation
    - Dynamic agent escalation mid-simulation
    - Early abort
    - Determinism control

    Internal implementation detail - do not import directly.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.base_url = self.config.mirofish_url
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

    async def run_simulation(
        self,
        question: str,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[PartialMiroFishResult]:
        """
        Run full MiroFish simulation with streaming.

        Yields partial results as simulation progresses.
        """
        context = context or {}

        try:
            # Start simulation
            simulation_id = await self.start_simulation(
                question=question,
                domain=domain,
                agents=self.config.base_agents,
            )

            # Stream partial results
            async for partial in self.stream_results(
                simulation_id, interval=self.config.stream_interval_seconds
            ):
                yield partial

            # Get final result
            final = await self.get_final_result(simulation_id)
            yield final

        except Exception as e:
            logger.error(f"Simulation error: {e}")
            raise

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

            # Add determinism seed if configured
            if self.config.determinism_seed is not None:
                data["seed"] = str(self.config.determinism_seed)

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
                            narrative=data.get("narrative"),
                            simulation_id=simulation_id,
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
    ) -> PartialMiroFishResult:
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
                            elapsed = time.time() - start_time
                            return PartialMiroFishResult(
                                probability=data.get("probability", 0.5),
                                confidence=data.get("confidence", 0.5),
                                agents_run=data.get("agents_completed", 0),
                                rounds_completed=data.get("rounds_completed", 0),
                                narrative=data.get("narrative", ""),
                                simulation_id=simulation_id,
                                duration_seconds=elapsed,
                                is_still_running=False,
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
