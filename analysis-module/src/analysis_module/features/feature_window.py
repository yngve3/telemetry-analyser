"""Feature vectors for a telemetry time window."""

from __future__ import annotations

from dataclasses import dataclass

from analysis_module.features.feature_vector import FeatureVector


@dataclass(frozen=True, slots=True)
class FeatureWindow:
    """Ordered feature vectors with a stable feature schema."""

    feature_names: tuple[str, ...]
    vectors: tuple[FeatureVector, ...]

    def __post_init__(self) -> None:
        for vector in self.vectors:
            if vector.names != self.feature_names:
                raise ValueError("All vectors in a window must share feature names.")

    def values_matrix(self) -> tuple[tuple[float, ...], ...]:
        return tuple(vector.values for vector in self.vectors)

    def __len__(self) -> int:
        return len(self.vectors)
