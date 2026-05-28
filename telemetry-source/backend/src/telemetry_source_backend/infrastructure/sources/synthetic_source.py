"""Synthetic telemetry source adapter."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import AsyncIterator

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import MissionPlan
from telemetry_source_backend.domain.synthetic.services.mission_runner import MissionRunner


MissionRunnerFactory = Callable[[MissionPlan], MissionRunner]


@dataclass(slots=True)
class SyntheticTelemetrySource:
    """Adapter that produces synthetic telemetry samples."""

    mission_plan: MissionPlan
    runner: MissionRunner | None = None
    runner_factory: MissionRunnerFactory = MissionRunner

    def __post_init__(self) -> None:
        if self.runner is None:
            self.runner = self.runner_factory(self.mission_plan)
            self.runner.start()

    async def read(self) -> TelemetrySample:
        assert self.runner is not None
        interval_sec = 1.0 / self.mission_plan.frequency_hz
        return self.runner.tick(interval_sec)

    async def stream(self) -> AsyncIterator[TelemetrySample]:
        assert self.runner is not None
        interval_sec = 1.0 / self.mission_plan.frequency_hz

        while not self.runner.is_completed:
            yield self.runner.tick(interval_sec)
            await asyncio.sleep(interval_sec)
