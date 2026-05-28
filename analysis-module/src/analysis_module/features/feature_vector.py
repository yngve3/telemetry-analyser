"""Single extracted telemetry feature vector."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureVector:
    """Feature values in a stable name order."""

    names: tuple[str, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.names) != len(self.values):
            raise ValueError("Feature names and values must have the same length.")

    def to_dict(self) -> dict[str, float]:
        return dict(zip(self.names, self.values, strict=True))
