"""Detector discovery routes."""

from fastapi import APIRouter

from analysis_service.presentation.api.schemas.detectors import (
    DetectorListResponse,
    DetectorResponse,
)

router = APIRouter(prefix="/analysis/detectors", tags=["analysis"])


@router.get("", response_model=DetectorListResponse)
async def list_detectors() -> DetectorListResponse:
    return DetectorListResponse(
        detectors=[
            DetectorResponse(
                name="rule_based",
                kind="rule_based",
                status="available",
                aliases=[],
            ),
            DetectorResponse(
                name="ml",
                kind="ml",
                status="requires_artifact",
                aliases=[],
            ),
            DetectorResponse(
                name="nn_autoencoder",
                kind="nn",
                status="requires_artifact",
                aliases=["nn", "neural_network"],
            ),
        ]
    )
