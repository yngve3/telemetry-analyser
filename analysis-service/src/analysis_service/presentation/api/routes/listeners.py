"""Telemetry ingestion listener routes."""

from fastapi import APIRouter, HTTPException, status

from analysis_service.application import (
    ListenerConfigurationError,
    ListenerNotFoundError,
)
from analysis_service.presentation.api.dependencies import IngestionManagerDep
from analysis_service.presentation.api.schemas.listeners import (
    ListenerCreateRequest,
    ListenerDeletedResponse,
    ListenerResponse,
)

router = APIRouter(prefix="/analysis/listeners", tags=["analysis"])


@router.post(
    "",
    response_model=ListenerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_listener(
    request: ListenerCreateRequest,
    manager: IngestionManagerDep,
) -> ListenerResponse:
    try:
        record = await manager.create_listener(request.to_config())
    except ListenerConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return ListenerResponse.from_record(record)


@router.get("", response_model=list[ListenerResponse])
async def list_listeners(manager: IngestionManagerDep) -> list[ListenerResponse]:
    return [
        ListenerResponse.from_record(record)
        for record in manager.list_listeners()
    ]


@router.get("/{listener_id}", response_model=ListenerResponse)
async def get_listener(
    listener_id: str,
    manager: IngestionManagerDep,
) -> ListenerResponse:
    try:
        return ListenerResponse.from_record(manager.get_listener(listener_id))
    except ListenerNotFoundError as exc:
        raise _listener_not_found(listener_id) from exc


@router.delete("/{listener_id}", response_model=ListenerDeletedResponse)
async def delete_listener(
    listener_id: str,
    manager: IngestionManagerDep,
) -> ListenerDeletedResponse:
    try:
        await manager.delete_listener(listener_id)
    except ListenerNotFoundError as exc:
        raise _listener_not_found(listener_id) from exc
    return ListenerDeletedResponse(listener_id=listener_id, deleted=True)


def _listener_not_found(listener_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Telemetry listener {listener_id!r} was not found.",
    )
