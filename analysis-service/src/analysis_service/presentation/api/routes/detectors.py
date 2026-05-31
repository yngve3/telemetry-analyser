"""Detector discovery routes."""

from fastapi import APIRouter

from analysis_service.application.model_registry import list_analysis_models
from analysis_service.presentation.api.schemas.detectors import (
    DetectorListResponse,
    DetectorResponse,
)

router = APIRouter(prefix="/analysis/detectors", tags=["analysis"])


@router.get("", response_model=DetectorListResponse)
async def list_detectors() -> DetectorListResponse:
    return DetectorListResponse(
        detectors=[
            DetectorResponse(**model.to_dict())
            for model in list_analysis_models()
        ]
    )
