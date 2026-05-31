"""Analysis model discovery routes."""

from fastapi import APIRouter

from analysis_service.application.model_registry import (
    list_analysis_models,
    list_model_profiles,
)
from analysis_service.presentation.api.schemas.models import (
    AnalysisModelListResponse,
    AnalysisModelProfileListResponse,
    AnalysisModelProfileResponse,
    AnalysisModelResponse,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/models", response_model=AnalysisModelListResponse)
async def list_models() -> AnalysisModelListResponse:
    return AnalysisModelListResponse(
        models=[
            AnalysisModelResponse(**model.to_dict())
            for model in list_analysis_models()
        ]
    )


@router.get(
    "/model-profiles",
    response_model=AnalysisModelProfileListResponse,
)
async def list_analysis_model_profiles() -> AnalysisModelProfileListResponse:
    return AnalysisModelProfileListResponse(
        profiles=[
            AnalysisModelProfileResponse(**profile.to_dict())
            for profile in list_model_profiles()
        ]
    )
