"""Mission script home point."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScriptHome:
    """Initial position and heading for a human-authored mission script."""

    latitude: float
    longitude: float
    altitude: float = 0.0
    heading_deg: float = 0.0
    battery: float = 100.0

