"""Mappers for snapshot source API schemas."""

from datetime import datetime

from telemetry_source_backend.application.ports import TelemetryValidator
from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.snapshot.models import (
    Snapshot,
    SnapshotConfig,
    SnapshotPlaybackMode,
)
from telemetry_source_backend.infrastructure.contracts.telemetry_contract import (
    telemetry_sample_to_contract_dict,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_snapshot_registry import (
    SnapshotRecord,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_snapshot_stream_registry import (
    SnapshotUdpStreamRecord,
)
from telemetry_source_backend.presentation.api.schemas.snapshot_requests import (
    SnapshotCreateRequest,
    SnapshotSampleRequest,
)
from telemetry_source_backend.presentation.api.schemas.snapshot_responses import (
    SnapshotListItemResponse,
    SnapshotStatusResponse,
    SnapshotUdpStreamStatusResponse,
)
from telemetry_source_backend.presentation.api.schemas.synthetic_responses import (
    TelemetrySampleResponse,
)


def snapshot_from_request(
    snapshot_id: str,
    request: SnapshotCreateRequest,
    validator: TelemetryValidator,
) -> Snapshot:
    samples = tuple(sample_from_request(sample) for sample in request.samples)
    for sample in samples:
        validator.validate_sample(sample)

    return Snapshot(
        snapshot_id=snapshot_id,
        config=SnapshotConfig(
            name=request.name,
            playback_mode=SnapshotPlaybackMode.SEND_ONCE,
            repeat=request.repeat,
            interval_seconds=request.interval_seconds,
        ),
        samples=samples,
    )


def sample_from_request(request: SnapshotSampleRequest) -> TelemetrySample:
    timestamp = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
    return TelemetrySample(
        timestamp=timestamp,
        drone_id=request.drone_id,
        latitude_deg=request.latitude_deg,
        longitude_deg=request.longitude_deg,
        altitude_m=request.altitude_m,
        battery_percent=request.battery_percent,
        satellites=request.satellites,
        ground_speed_m_s=request.ground_speed_m_s,
        vertical_speed_m_s=request.vertical_speed_m_s,
        heading_deg=request.heading_deg,
        relative_altitude_m=request.relative_altitude_m,
        velocity_x_m_s=request.velocity_x_m_s,
        velocity_y_m_s=request.velocity_y_m_s,
        velocity_z_m_s=request.velocity_z_m_s,
        roll_rad=request.roll_rad,
        pitch_rad=request.pitch_rad,
        yaw_rad=request.yaw_rad,
        roll_rate_rad_s=request.roll_rate_rad_s,
        pitch_rate_rad_s=request.pitch_rate_rad_s,
        yaw_rate_rad_s=request.yaw_rate_rad_s,
        satellites_visible=request.satellites_visible,
        gps_fix_type=request.gps_fix_type,
        gps_eph=request.gps_eph,
        gps_epv=request.gps_epv,
        battery_voltage_v=request.battery_voltage_v,
        battery_current_a=request.battery_current_a,
        system_status=request.system_status,
        flight_mode=request.flight_mode,
        armed=request.armed,
        sensor_health_flags=request.sensor_health_flags,
    )


def telemetry_sample_response(
    sample: TelemetrySample,
    validator: TelemetryValidator,
) -> TelemetrySampleResponse:
    payload = telemetry_sample_to_contract_dict(sample)
    validator.validate_payload(payload)
    return TelemetrySampleResponse(**payload)


def snapshot_status_response(record: SnapshotRecord) -> SnapshotStatusResponse:
    return SnapshotStatusResponse(
        snapshot_id=record.snapshot_id,
        name=record.snapshot.config.name,
        samples_count=len(record.snapshot.samples),
        interval_seconds=record.snapshot.config.interval_seconds,
        repeat=record.snapshot.config.repeat,
    )


def snapshot_list_item_response(record: SnapshotRecord) -> SnapshotListItemResponse:
    return SnapshotListItemResponse(
        snapshot_id=record.snapshot_id,
        name=record.snapshot.config.name,
        samples_count=len(record.snapshot.samples),
    )


def snapshot_udp_stream_status_response(
    record: SnapshotUdpStreamRecord,
) -> SnapshotUdpStreamStatusResponse:
    return SnapshotUdpStreamStatusResponse(
        stream_id=record.stream_id,
        snapshot_id=record.snapshot_id,
        host=record.host,
        port=record.port,
        frequency_hz=record.frequency_hz,
        repeat=record.repeat,
        is_active=record.is_active,
        samples_sent=record.samples_sent,
        frames_sent=record.frames_sent,
    )
