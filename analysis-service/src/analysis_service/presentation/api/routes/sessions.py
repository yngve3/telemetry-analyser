"""Analysis session routes."""

from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi import APIRouter, HTTPException, status
from telemetry_converter import (
    ConversionError,
    TelemetryInputFormat,
    UnifiedTelemetryPayload,
    convert,
)

from analysis_service.application import (
    SessionNotFoundError,
    unified_telemetry_from_converter_payload,
    unified_telemetry_from_mapping,
    unified_telemetry_to_dict,
)
from analysis_service.presentation.api.dependencies import (
    IngestionManagerDep,
    SessionManagerDep,
    TelemetrySchemaValidatorDep,
)
from analysis_service.presentation.api.schemas.analysis import (
    AnalyzeRequest,
    TelemetryPayloadFormat,
)
from analysis_service.presentation.api.schemas.profiles import AnalysisProfileRequest
from analysis_service.presentation.api.schemas.sessions import (
    AnalysisSessionCreateRequest,
    AnalysisSessionDeletedResponse,
    AnalysisSessionLastTelemetryResponse,
    AnalysisSessionLastResultResponse,
    AnalysisSessionResponse,
    AnalysisSessionStateResponse,
)
from analysis_service.validation import (
    JsonSchemaTelemetryValidator,
    TelemetryValidationError,
)

router = APIRouter(prefix="/analysis/sessions", tags=["analysis"])

_MAX_PAYLOAD_BASE64_LENGTH = 65_536


@router.post(
    "",
    response_model=AnalysisSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: AnalysisSessionCreateRequest,
    manager: SessionManagerDep,
) -> AnalysisSessionResponse:
    try:
        session = manager.create_session(
            session_id=request.session_id,
            drone_id=request.drone_id,
            profile=(
                None
                if request.profile is None
                else request.profile.to_profile()
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AnalysisSessionResponse.from_session(session)


@router.get("/{session_id}", response_model=AnalysisSessionResponse)
async def get_session(
    session_id: str,
    manager: SessionManagerDep,
) -> AnalysisSessionResponse:
    try:
        return AnalysisSessionResponse.from_session(manager.get_session(session_id))
    except SessionNotFoundError as exc:
        raise _session_not_found(session_id) from exc


@router.put("/{session_id}/profile", response_model=AnalysisSessionResponse)
async def update_session_profile(
    session_id: str,
    request: AnalysisProfileRequest,
    manager: SessionManagerDep,
) -> AnalysisSessionResponse:
    try:
        session = manager.update_session_profile(session_id, request.to_profile())
    except SessionNotFoundError as exc:
        raise _session_not_found(session_id) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AnalysisSessionResponse.from_session(session)


@router.delete("/{session_id}", response_model=AnalysisSessionDeletedResponse)
async def delete_session(
    session_id: str,
    manager: SessionManagerDep,
    ingestion_manager: IngestionManagerDep,
) -> AnalysisSessionDeletedResponse:
    try:
        await ingestion_manager.delete_listeners_for_session(session_id)
        manager.delete_session(session_id)
    except SessionNotFoundError as exc:
        raise _session_not_found(session_id) from exc
    return AnalysisSessionDeletedResponse(session_id=session_id, deleted=True)


@router.get("/{session_id}/last-result", response_model=AnalysisSessionLastResultResponse)
async def get_session_last_result(
    session_id: str,
    manager: SessionManagerDep,
) -> AnalysisSessionLastResultResponse:
    try:
        result = manager.get_last_result(session_id)
    except SessionNotFoundError as exc:
        raise _session_not_found(session_id) from exc
    return AnalysisSessionLastResultResponse(
        session_id=session_id,
        result=None if result is None else result.to_dict(),
    )


@router.get(
    "/{session_id}/last-telemetry",
    response_model=AnalysisSessionLastTelemetryResponse,
)
async def get_session_last_telemetry(
    session_id: str,
    manager: SessionManagerDep,
) -> AnalysisSessionLastTelemetryResponse:
    try:
        telemetry = manager.get_last_telemetry(session_id)
    except SessionNotFoundError as exc:
        raise _session_not_found(session_id) from exc
    return AnalysisSessionLastTelemetryResponse(
        session_id=session_id,
        telemetry=None if telemetry is None else unified_telemetry_to_dict(telemetry),
    )


@router.get("/{session_id}/state", response_model=AnalysisSessionStateResponse)
async def get_session_state(
    session_id: str,
    manager: SessionManagerDep,
) -> AnalysisSessionStateResponse:
    try:
        session = manager.get_session(session_id)
    except SessionNotFoundError as exc:
        raise _session_not_found(session_id) from exc
    return AnalysisSessionStateResponse(
        session=AnalysisSessionResponse.from_session(session),
        last_telemetry=(
            None
            if session.last_telemetry is None
            else unified_telemetry_to_dict(session.last_telemetry)
        ),
        last_result=(
            None
            if session.last_result is None
            else session.last_result.to_dict()
        ),
    )


@router.post("/{session_id}/analyze")
async def analyze(
    session_id: str,
    request: AnalyzeRequest,
    manager: SessionManagerDep,
    telemetry_validator: TelemetrySchemaValidatorDep,
) -> dict[str, Any]:
    telemetry = _telemetry_from_request(request, telemetry_validator)
    try:
        result = manager.analyze(session_id, telemetry)
    except TelemetryValidationError as exc:
        raise _bad_telemetry_request(exc) from exc
    except SessionNotFoundError as exc:
        raise _session_not_found(session_id) from exc
    return result.to_dict()


def _telemetry_from_request(
    request: AnalyzeRequest,
    telemetry_validator: JsonSchemaTelemetryValidator,
):
    if request.format is TelemetryPayloadFormat.UNIFIED_TELEMETRY:
        if request.telemetry is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Field `telemetry` is required for unified.telemetry payloads.",
            )
        try:
            telemetry_validator.validate_payload(request.telemetry)
        except TelemetryValidationError as exc:
            raise _bad_telemetry_request(exc) from exc
        return unified_telemetry_from_mapping(request.telemetry)

    if request.payload_base64 is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field `payload_base64` is required for mavlink.v2 payloads.",
        )
    if len(request.payload_base64) > _MAX_PAYLOAD_BASE64_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field `payload_base64` is too large.",
        )

    try:
        payload = base64.b64decode(request.payload_base64, validate=True)
    except binascii.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field `payload_base64` must contain valid base64 data.",
        ) from exc

    try:
        converted = convert(payload, source_format=TelemetryInputFormat.MAVLINK_V2)
    except ConversionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not isinstance(converted, UnifiedTelemetryPayload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Converted telemetry payload has an unsupported type.",
        )
    try:
        telemetry_validator.validate_payload(converted.to_dict())
    except TelemetryValidationError as exc:
        raise _bad_telemetry_request(exc) from exc
    return unified_telemetry_from_converter_payload(converted)


def _session_not_found(session_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Analysis session {session_id!r} was not found.",
    )


def _bad_telemetry_request(exc: TelemetryValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=exc.to_detail(),
    )
