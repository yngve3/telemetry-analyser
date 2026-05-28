"""Model artifact contract validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class ModelArtifactError(ValueError):
    """Raised when a model artifact package is invalid."""


@dataclass(frozen=True, slots=True)
class ModelArtifactMetadata:
    """Validated metadata for a telemetry scoring artifact."""

    model_type: str
    feature_version: str
    window_size: int
    feature_names: tuple[str, ...]
    created_at: datetime

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        expected_feature_names: Sequence[str] | None = None,
    ) -> "ModelArtifactMetadata":
        model_type = _required_str(payload, "model_type")
        feature_version = _required_str(payload, "feature_version")
        window_size = _required_positive_int(payload, "window_size")
        feature_names = _required_str_tuple(payload, "feature_names")
        created_at = _required_datetime(payload, "created_at")

        if expected_feature_names is not None:
            expected = tuple(expected_feature_names)
            if feature_names != expected:
                raise ModelArtifactError(
                    "Artifact feature_names do not match the extractor feature order."
                )

        return cls(
            model_type=model_type,
            feature_version=feature_version,
            window_size=window_size,
            feature_names=feature_names,
            created_at=created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "feature_version": self.feature_version,
            "window_size": self.window_size,
            "feature_names": list(self.feature_names),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    """Validated model artifact package description."""

    metadata: ModelArtifactMetadata
    threshold: float
    normalizer: Mapping[str, Any]


def parse_model_artifact(
    metadata_payload: Mapping[str, Any],
    threshold_payload: Mapping[str, Any],
    normalizer_payload: Mapping[str, Any],
    expected_feature_names: Sequence[str] | None = None,
) -> ModelArtifact:
    metadata = ModelArtifactMetadata.from_dict(
        metadata_payload,
        expected_feature_names=expected_feature_names,
    )
    threshold = _required_number(threshold_payload, "threshold")
    if threshold < 0.0:
        raise ModelArtifactError("Artifact threshold must not be negative.")

    return ModelArtifact(
        metadata=metadata,
        threshold=threshold,
        normalizer=dict(normalizer_payload),
    )


def _required_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ModelArtifactError(f"Artifact metadata field `{key}` must be a string.")
    return value


def _required_positive_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ModelArtifactError(
            f"Artifact metadata field `{key}` must be a positive integer."
        )
    return value


def _required_str_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ModelArtifactError(
            f"Artifact metadata field `{key}` must be a non-empty string array."
        )
    return tuple(value)


def _required_datetime(payload: Mapping[str, Any], key: str) -> datetime:
    value = _required_str(payload, key)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ModelArtifactError(
            f"Artifact metadata field `{key}` must be an ISO datetime."
        ) from exc


def _required_number(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise ModelArtifactError(f"Artifact field `{key}` must be numeric.")
    return float(value)
