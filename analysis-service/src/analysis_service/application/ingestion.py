"""In-memory telemetry ingestion listener management."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from analysis_module import AnomalyResult

from analysis_service.application.sessions import (
    SessionManager,
    SessionNotFoundError,
)


class ListenerConfigurationError(ValueError):
    """Raised when a telemetry listener cannot be configured."""


class ListenerNotFoundError(KeyError):
    """Raised when a telemetry listener does not exist."""


class ListenerProtocol(StrEnum):
    UDP = "udp"


class ListenerPayloadFormat(StrEnum):
    MAVLINK_V2 = "mavlink.v2"


class ListenerStatus(StrEnum):
    STARTING = "starting"
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ListenerConfig:
    """Configuration for an inbound telemetry listener."""

    session_id: str
    protocol: ListenerProtocol
    format: ListenerPayloadFormat
    bind_host: str
    bind_port: int
    buffer_size: int = 4096


@dataclass(slots=True)
class ListenerRecord:
    """Runtime listener state exposed through the API."""

    listener_id: str
    config: ListenerConfig
    status: ListenerStatus = ListenerStatus.STARTING
    received_packets: int = 0
    received_bytes: int = 0
    converted_samples: int = 0
    analysis_errors: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    last_received_at: datetime | None = None
    last_remote_address: str | None = None
    last_remote_port: int | None = None
    last_telemetry_timestamp: datetime | None = None
    last_result: AnomalyResult | None = None
    last_error: str | None = None
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task[None] | None = None

    def mark_active(self) -> None:
        self.status = ListenerStatus.ACTIVE
        self.last_error = None

    def mark_stopped(self) -> None:
        if self.status is not ListenerStatus.ERROR:
            self.status = ListenerStatus.STOPPED

    def mark_error(self, error: str) -> None:
        self.status = ListenerStatus.ERROR
        self.last_error = error

    def observe_packet(self, payload_size: int, remote: tuple[str, int]) -> None:
        self.received_packets += 1
        self.received_bytes += payload_size
        self.last_received_at = datetime.now(tz=UTC)
        self.last_remote_address = remote[0]
        self.last_remote_port = remote[1]

    def observe_result(self, result: AnomalyResult) -> None:
        self.converted_samples += 1
        self.last_result = result
        self.last_telemetry_timestamp = result.telemetry_timestamp

    def observe_analysis_error(self, error: str) -> None:
        self.analysis_errors += 1
        self.last_error = error

    def to_dict(self, include_last_result: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "listener_id": self.listener_id,
            "session_id": self.config.session_id,
            "protocol": self.config.protocol.value,
            "format": self.config.format.value,
            "bind_host": self.config.bind_host,
            "bind_port": self.config.bind_port,
            "status": self.status.value,
            "received_packets": self.received_packets,
            "received_bytes": self.received_bytes,
            "converted_samples": self.converted_samples,
            "analysis_errors": self.analysis_errors,
            "created_at": self.created_at.isoformat(),
            "last_received_at": _datetime_to_str(self.last_received_at),
            "last_remote_address": self.last_remote_address,
            "last_remote_port": self.last_remote_port,
            "last_telemetry_timestamp": _datetime_to_str(self.last_telemetry_timestamp),
            "last_error": self.last_error,
        }
        if include_last_result:
            payload["last_result"] = (
                None
                if self.last_result is None
                else self.last_result.to_dict()
            )
        return payload


class TelemetryListener(Protocol):
    """Runtime listener implementation contract."""

    async def run(
        self,
        record: ListenerRecord,
        session_manager: SessionManager,
    ) -> None:
        ...


ListenerFactory = Callable[[ListenerConfig], TelemetryListener]


class IngestionManager:
    """Creates and tracks inbound telemetry listeners."""

    def __init__(
        self,
        session_manager: SessionManager,
        listener_factory: ListenerFactory,
    ) -> None:
        self._session_manager = session_manager
        self._listener_factory = listener_factory
        self._listeners: dict[str, ListenerRecord] = {}

    async def create_listener(
        self,
        config: ListenerConfig,
        listener_id: str | None = None,
    ) -> ListenerRecord:
        self._validate_config(config)
        resolved_listener_id = listener_id or str(uuid4())
        if resolved_listener_id in self._listeners:
            raise ListenerConfigurationError(
                f"Telemetry listener `{resolved_listener_id}` already exists."
            )

        record = ListenerRecord(
            listener_id=resolved_listener_id,
            config=config,
        )
        listener = self._listener_factory(config)
        record.task = asyncio.create_task(
            listener.run(record, self._session_manager)
        )
        self._listeners[record.listener_id] = record
        await self._wait_for_listener_start(record)
        if record.status is ListenerStatus.ERROR:
            self._listeners.pop(record.listener_id, None)
            raise ListenerConfigurationError(
                record.last_error or "Telemetry listener could not be started."
            )
        return record

    def list_listeners(self) -> tuple[ListenerRecord, ...]:
        return tuple(self._listeners.values())

    def get_listener(self, listener_id: str) -> ListenerRecord:
        record = self._listeners.get(listener_id)
        if record is None:
            raise ListenerNotFoundError(listener_id)
        return record

    async def delete_listener(self, listener_id: str) -> ListenerRecord:
        record = self._listeners.pop(listener_id, None)
        if record is None:
            raise ListenerNotFoundError(listener_id)
        await self._stop_record(record)
        return record

    async def delete_listeners_for_session(
        self,
        session_id: str,
    ) -> tuple[ListenerRecord, ...]:
        records = tuple(
            record
            for record in self._listeners.values()
            if record.config.session_id == session_id
        )
        for record in records:
            self._listeners.pop(record.listener_id, None)
            await self._stop_record(record)
        return records

    async def shutdown(self) -> None:
        listener_ids = tuple(self._listeners)
        for listener_id in listener_ids:
            try:
                await self.delete_listener(listener_id)
            except ListenerNotFoundError:
                continue

    def _validate_config(self, config: ListenerConfig) -> None:
        try:
            self._session_manager.get_session(config.session_id)
        except SessionNotFoundError as exc:
            raise ListenerConfigurationError(
                f"Analysis session {config.session_id!r} was not found."
            ) from exc
        if config.protocol is not ListenerProtocol.UDP:
            raise ListenerConfigurationError("Only UDP listeners are supported.")
        if config.format is not ListenerPayloadFormat.MAVLINK_V2:
            raise ListenerConfigurationError("Only mavlink.v2 listeners are supported.")
        for record in self._listeners.values():
            if record.status not in (ListenerStatus.STARTING, ListenerStatus.ACTIVE):
                continue
            if (
                record.config.protocol == config.protocol
                and record.config.bind_host == config.bind_host
                and record.config.bind_port == config.bind_port
            ):
                raise ListenerConfigurationError(
                    "Telemetry listener already exists on "
                    f"{config.bind_host}:{config.bind_port}."
                )

    async def _wait_for_listener_start(self, record: ListenerRecord) -> None:
        for _ in range(10):
            if record.status in (ListenerStatus.ACTIVE, ListenerStatus.ERROR):
                return
            await asyncio.sleep(0.01)

    async def _stop_record(self, record: ListenerRecord) -> None:
        record.stop_event.set()
        if record.task is not None:
            record.task.cancel()
            try:
                await record.task
            except asyncio.CancelledError:
                pass
        record.mark_stopped()


def _datetime_to_str(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
