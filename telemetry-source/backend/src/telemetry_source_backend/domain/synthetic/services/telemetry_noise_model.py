"""Deterministic telemetry noise model."""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import NoiseProfile

METERS_PER_DEGREE_LAT = 111_320.0


class TelemetryNoiseModel:
    """Applies deterministic pseudo-random noise to telemetry samples."""

    def apply(
        self,
        sample: TelemetrySample,
        profile: NoiseProfile,
        elapsed_sec: float,
    ) -> TelemetrySample:
        if profile.random_seed is None:
            return sample

        latitude_noise_m = self._gauss(profile.random_seed, elapsed_sec, "lat")
        longitude_noise_m = self._gauss(profile.random_seed, elapsed_sec, "lon")
        altitude_noise_m = self._gauss(profile.random_seed, elapsed_sec, "alt")
        speed_noise = self._gauss(profile.random_seed, elapsed_sec, "speed")
        heading_noise = self._gauss(profile.random_seed, elapsed_sec, "heading")
        battery_noise = self._gauss(profile.random_seed, elapsed_sec, "battery")

        latitude = sample.latitude_deg + (
            latitude_noise_m
            * profile.gps_position_std_m
            / METERS_PER_DEGREE_LAT
        )
        longitude_scale = max(
            METERS_PER_DEGREE_LAT * abs(math.cos(math.radians(sample.latitude_deg))),
            1.0,
        )
        longitude = sample.longitude_deg + (
            longitude_noise_m * profile.gps_position_std_m / longitude_scale
        )

        return replace(
            sample,
            latitude_deg=latitude,
            longitude_deg=longitude,
            altitude_m=sample.altitude_m
            + altitude_noise_m * profile.altitude_std_m,
            ground_speed_m_s=self._optional_non_negative(
                sample.ground_speed_m_s,
                speed_noise * profile.speed_std_m_s,
            ),
            heading_deg=(
                (sample.heading_deg + heading_noise * profile.heading_std_deg) % 360
                if sample.heading_deg is not None
                else None
            ),
            battery_percent=min(
                max(
                    sample.battery_percent
                    + battery_noise * profile.battery_std_percent,
                    0.0,
                ),
                100.0,
            ),
        )

    def _gauss(self, seed: int, elapsed_sec: float, key: str) -> float:
        bucket = round(elapsed_sec, 2)
        digest = hashlib.sha256(f"{seed}:{bucket}:{key}".encode("utf-8")).digest()
        local_seed = int.from_bytes(digest[:8], "little")
        return random.Random(local_seed).gauss(0.0, 1.0)

    def _optional_non_negative(
        self,
        value: float | None,
        delta: float,
    ) -> float | None:
        if value is None:
            return None

        return max(value + delta, 0.0)
