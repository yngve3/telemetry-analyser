"""Analysis profile routes."""

from fastapi import APIRouter, HTTPException, status

from analysis_service.presentation.api.dependencies import SessionManagerDep
from analysis_service.presentation.api.schemas.profiles import (
    AnalysisProfileRequest,
    AnalysisProfileResponse,
)

router = APIRouter(prefix="/analysis/profile", tags=["analysis"])


@router.get("", response_model=AnalysisProfileResponse)
async def get_profile(manager: SessionManagerDep) -> AnalysisProfileResponse:
    return AnalysisProfileResponse.from_profile(manager.get_profile())


@router.put("", response_model=AnalysisProfileResponse)
async def update_profile(
    request: AnalysisProfileRequest,
    manager: SessionManagerDep,
) -> AnalysisProfileResponse:
    try:
        profile = manager.update_profile(request.to_profile())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AnalysisProfileResponse.from_profile(profile)
