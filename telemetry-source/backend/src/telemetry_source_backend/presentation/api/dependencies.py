"""FastAPI dependency providers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from telemetry_source_backend.application.ports import (
    TelemetryFrameEncoder,
    TelemetryTransport,
    TelemetryValidator,
)
from telemetry_source_backend.application.use_cases.publish_snapshot import (
    SnapshotUdpPublisher,
)
from telemetry_source_backend.domain.synthetic.script.models import MissionScript
from telemetry_source_backend.domain.synthetic.script.services import (
    MissionScriptCompiler,
)
from telemetry_source_backend.domain.synthetic.services.mission_runner import (
    MissionRunner,
)
from telemetry_source_backend.domain.external.services import ExternalConnectionPolicy
from telemetry_source_backend.infrastructure.persistence.in_memory_external_source_registry import (
    ExternalSourceRecord,
    InMemoryExternalSourceRegistry,
)
from telemetry_source_backend.infrastructure.contracts.telemetry_contract import (
    TelemetryContractValidator,
)
from telemetry_source_backend.infrastructure.encoders.mavlink_encoder import (
    MavlinkTelemetryEncoder,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_snapshot_registry import (
    InMemorySnapshotRegistry,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_snapshot_stream_registry import (
    InMemorySnapshotStreamRegistry,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_synthetic_mission_registry import (
    InMemorySyntheticMissionRegistry,
    SyntheticMissionRecord,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_synthetic_stream_registry import (
    InMemorySyntheticStreamRegistry,
)
from telemetry_source_backend.infrastructure.transports.udp_transport import (
    UdpTelemetryTransport,
)
from telemetry_source_backend.infrastructure.sources.external_source import (
    ExternalUdpTelemetrySource,
)
from telemetry_source_backend.presentation.api.schemas.synthetic_requests import (
    UdpStreamRequest,
)


@dataclass(frozen=True, slots=True)
class SyntheticMissionBuilder:
    """Builds runtime mission records from domain mission scripts."""

    compiler: MissionScriptCompiler

    def build(self, script: MissionScript) -> SyntheticMissionRecord:
        plan = self.compiler.compile(script)
        runner = MissionRunner(plan)
        return SyntheticMissionRecord(
            mission_id=runner.mission_id,
            script=script,
            plan=plan,
            runner=runner,
        )


@dataclass(frozen=True, slots=True)
class UdpPublicationDependencies:
    """Dependencies needed to publish a MAVLink-over-UDP stream."""

    request: UdpStreamRequest
    encoder: TelemetryFrameEncoder
    transport: TelemetryTransport
    validator: TelemetryValidator
    snapshot_publisher: SnapshotUdpPublisher


@dataclass(frozen=True, slots=True)
class ExternalSourceRuntimeDependencies:
    """Dependencies needed to receive packets from an external source."""

    receiver: ExternalUdpTelemetrySource
    forward_transport: TelemetryTransport | None = None


@lru_cache(maxsize=1)
def get_synthetic_mission_registry() -> InMemorySyntheticMissionRegistry:
    return InMemorySyntheticMissionRegistry()


@lru_cache(maxsize=1)
def get_synthetic_stream_registry() -> InMemorySyntheticStreamRegistry:
    return InMemorySyntheticStreamRegistry()


@lru_cache(maxsize=1)
def get_snapshot_registry() -> InMemorySnapshotRegistry:
    return InMemorySnapshotRegistry()


@lru_cache(maxsize=1)
def get_snapshot_stream_registry() -> InMemorySnapshotStreamRegistry:
    return InMemorySnapshotStreamRegistry()


@lru_cache(maxsize=1)
def get_external_source_registry() -> InMemoryExternalSourceRegistry:
    return InMemoryExternalSourceRegistry()


@lru_cache(maxsize=1)
def get_mission_script_compiler() -> MissionScriptCompiler:
    return MissionScriptCompiler()


@lru_cache(maxsize=1)
def get_telemetry_contract_validator() -> TelemetryValidator:
    return TelemetryContractValidator.load_default()


@lru_cache(maxsize=1)
def get_external_connection_policy() -> ExternalConnectionPolicy:
    return ExternalConnectionPolicy()


def get_synthetic_mission_builder(
    compiler: Annotated[MissionScriptCompiler, Depends(get_mission_script_compiler)],
) -> SyntheticMissionBuilder:
    return SyntheticMissionBuilder(compiler=compiler)


def get_udp_stream_request(request: UdpStreamRequest) -> UdpStreamRequest:
    return request


def get_mavlink_frame_encoder() -> TelemetryFrameEncoder:
    return MavlinkTelemetryEncoder()


def get_udp_transport(
    request: Annotated[UdpStreamRequest, Depends(get_udp_stream_request)],
) -> TelemetryTransport:
    return UdpTelemetryTransport(request.host, request.port)


def get_udp_publication_dependencies(
    request: Annotated[UdpStreamRequest, Depends(get_udp_stream_request)],
    encoder: Annotated[TelemetryFrameEncoder, Depends(get_mavlink_frame_encoder)],
    transport: Annotated[TelemetryTransport, Depends(get_udp_transport)],
    validator: Annotated[
        TelemetryValidator,
        Depends(get_telemetry_contract_validator),
    ],
) -> UdpPublicationDependencies:
    snapshot_publisher = SnapshotUdpPublisher(
        encoder=encoder,
        transport=transport,
        validator=validator,
    )
    return UdpPublicationDependencies(
        request=request,
        encoder=encoder,
        transport=transport,
        validator=validator,
        snapshot_publisher=snapshot_publisher,
    )


def get_external_source_record(
    source_id: str,
    registry: Annotated[
        InMemoryExternalSourceRegistry,
        Depends(get_external_source_registry),
    ],
) -> ExternalSourceRecord | None:
    return registry.get(source_id)


def get_external_runtime_dependencies(
    record: Annotated[ExternalSourceRecord | None, Depends(get_external_source_record)],
) -> ExternalSourceRuntimeDependencies | None:
    if record is None:
        return None
    forward_transport = (
        UdpTelemetryTransport(
            record.config.forward_host,
            record.config.forward_port,
        )
        if record.config.forward_enabled
        else None
    )
    return ExternalSourceRuntimeDependencies(
        receiver=ExternalUdpTelemetrySource(record.config),
        forward_transport=forward_transport,
    )


SyntheticMissionRegistryDep = Annotated[
    InMemorySyntheticMissionRegistry,
    Depends(get_synthetic_mission_registry),
]
SyntheticStreamRegistryDep = Annotated[
    InMemorySyntheticStreamRegistry,
    Depends(get_synthetic_stream_registry),
]
SnapshotRegistryDep = Annotated[
    InMemorySnapshotRegistry,
    Depends(get_snapshot_registry),
]
SnapshotStreamRegistryDep = Annotated[
    InMemorySnapshotStreamRegistry,
    Depends(get_snapshot_stream_registry),
]
ExternalSourceRegistryDep = Annotated[
    InMemoryExternalSourceRegistry,
    Depends(get_external_source_registry),
]
ExternalSourceRecordDep = Annotated[
    ExternalSourceRecord | None,
    Depends(get_external_source_record),
]
ExternalSourceRuntimeDep = Annotated[
    ExternalSourceRuntimeDependencies | None,
    Depends(get_external_runtime_dependencies),
]
ExternalConnectionPolicyDep = Annotated[
    ExternalConnectionPolicy,
    Depends(get_external_connection_policy),
]
SyntheticMissionBuilderDep = Annotated[
    SyntheticMissionBuilder,
    Depends(get_synthetic_mission_builder),
]
TelemetryValidatorDep = Annotated[
    TelemetryValidator,
    Depends(get_telemetry_contract_validator),
]
UdpPublicationDep = Annotated[
    UdpPublicationDependencies,
    Depends(get_udp_publication_dependencies),
]
