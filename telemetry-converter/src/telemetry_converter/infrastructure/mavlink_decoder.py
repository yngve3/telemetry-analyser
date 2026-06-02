"""MAVLink v2 telemetry decoder adapter."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Any

from telemetry_converter.domain.models import UnifiedTelemetryPayload

MAVLINK_V2_MAGIC = 0xFD
MAVLINK_V2_HEADER_LENGTH = 10
MAVLINK_CHECKSUM_LENGTH = 2
MAVLINK_SIGNATURE_LENGTH = 13
MAVLINK_SIGNED_INCOMPAT_FLAG = 0x01

HEARTBEAT_MSG_ID = 0
SYS_STATUS_MSG_ID = 1
GPS_RAW_INT_MSG_ID = 24
ATTITUDE_MSG_ID = 30
GLOBAL_POSITION_INT_MSG_ID = 33

HEARTBEAT_CRC_EXTRA = 50
SYS_STATUS_CRC_EXTRA = 124
GPS_RAW_INT_CRC_EXTRA = 24
ATTITUDE_CRC_EXTRA = 39
GLOBAL_POSITION_INT_CRC_EXTRA = 104

MAV_MODE_FLAG_SAFETY_ARMED = 128

CRC_EXTRAS = {
    HEARTBEAT_MSG_ID: HEARTBEAT_CRC_EXTRA,
    SYS_STATUS_MSG_ID: SYS_STATUS_CRC_EXTRA,
    GPS_RAW_INT_MSG_ID: GPS_RAW_INT_CRC_EXTRA,
    ATTITUDE_MSG_ID: ATTITUDE_CRC_EXTRA,
    GLOBAL_POSITION_INT_MSG_ID: GLOBAL_POSITION_INT_CRC_EXTRA,
}

_ATTITUDE_GROUP = "attitude"
_POSITION_GROUP = "position"
_GPS_GROUP = "gps"
_SYSTEM_GROUP = "system"
_MESSAGE_GROUPS = (
    _ATTITUDE_GROUP,
    _POSITION_GROUP,
    _GPS_GROUP,
    _SYSTEM_GROUP,
)
_GROUP_MAX_AGE_MS = {
    _ATTITUDE_GROUP: 250,
    _POSITION_GROUP: 750,
    _GPS_GROUP: 1_500,
    _SYSTEM_GROUP: 3_000,
}
_MIN_UNIX_GPS_TIMESTAMP_US = int(
    datetime(2000, 1, 1, tzinfo=UTC).timestamp() * 1_000_000
)


class MavlinkDecodeError(ValueError):
    """Raised when a MAVLink payload cannot be decoded."""


@dataclass(frozen=True, slots=True)
class _MavlinkFrame:
    system_id: int
    component_id: int
    message_id: int
    payload: bytes


class MavlinkV2TelemetryDecoder:
    """Decodes the MAVLink v2 telemetry subset published by telemetry-source."""

    def decode(self, payload: bytes) -> UnifiedTelemetryPayload:
        frames = _parse_frames(payload)
        if not frames:
            raise MavlinkDecodeError("MAVLink payload does not contain frames.")

        values: dict[str, Any] = {
            "drone_id": _drone_id(frames[0].system_id),
        }
        for frame in frames:
            self._apply_frame(frame, values)

        _apply_snapshot_freshness(values, frames)
        return _build_unified_telemetry(values)

    def _apply_frame(self, frame: _MavlinkFrame, values: dict[str, Any]) -> None:
        if frame.message_id == HEARTBEAT_MSG_ID:
            _apply_heartbeat(frame.payload, values)
        elif frame.message_id == ATTITUDE_MSG_ID:
            _apply_attitude(frame.payload, values)
        elif frame.message_id == GLOBAL_POSITION_INT_MSG_ID:
            _apply_global_position_int(frame.payload, values)
        elif frame.message_id == GPS_RAW_INT_MSG_ID:
            _apply_gps_raw_int(frame.payload, values)
        elif frame.message_id == SYS_STATUS_MSG_ID:
            _apply_sys_status(frame.payload, values)


class MavlinkV2TelemetryStreamDecoder:
    """Accumulates multi-rate MAVLink frames into telemetry snapshots."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._boot_time_epoch: datetime | None = None
        self._updated_at_s: dict[str, float] = {}

    def update(self, payload: bytes) -> UnifiedTelemetryPayload | None:
        frames = _parse_frames(payload)
        if not frames:
            raise MavlinkDecodeError("MAVLink payload does not contain frames.")

        for frame in frames:
            self._apply_frame(frame)

        if not _has_required_telemetry_fields(self._values):
            return None

        _apply_stream_freshness(self._values, self._updated_at_s, monotonic())
        return _build_unified_telemetry(self._values)

    def _apply_frame(self, frame: _MavlinkFrame) -> None:
        drone_id = _drone_id(frame.system_id)
        if self._values.get("drone_id") != drone_id:
            self._values = {"drone_id": drone_id}
            self._boot_time_epoch = None
            self._updated_at_s = {}

        if frame.message_id == HEARTBEAT_MSG_ID:
            _apply_heartbeat(frame.payload, self._values)
            self._mark_message_group(_SYSTEM_GROUP)
        elif frame.message_id == ATTITUDE_MSG_ID:
            _apply_attitude(frame.payload, self._values)
            self._mark_message_group(_ATTITUDE_GROUP)
            self._update_timestamp_from_boot_time()
        elif frame.message_id == GLOBAL_POSITION_INT_MSG_ID:
            _apply_global_position_int(frame.payload, self._values)
            self._mark_message_group(_POSITION_GROUP)
            self._update_timestamp_from_boot_time()
        elif frame.message_id == GPS_RAW_INT_MSG_ID:
            _apply_gps_raw_int(frame.payload, self._values)
            self._mark_message_group(_GPS_GROUP)
            self._anchor_boot_time()
        elif frame.message_id == SYS_STATUS_MSG_ID:
            _apply_sys_status(frame.payload, self._values)
            self._mark_message_group(_SYSTEM_GROUP)

    def _mark_message_group(self, group: str) -> None:
        self._updated_at_s[group] = monotonic()

    def _anchor_boot_time(self) -> None:
        timestamp = self._values.get("timestamp")
        time_boot_ms = self._values.get("_time_boot_ms")
        if isinstance(timestamp, datetime) and isinstance(time_boot_ms, int):
            self._boot_time_epoch = timestamp - timedelta(milliseconds=time_boot_ms)

    def _update_timestamp_from_boot_time(self) -> None:
        time_boot_ms = self._values.get("_time_boot_ms")
        if self._boot_time_epoch is not None and isinstance(time_boot_ms, int):
            self._values["timestamp"] = (
                self._boot_time_epoch + timedelta(milliseconds=time_boot_ms)
            )


def _parse_frames(data: bytes) -> tuple[_MavlinkFrame, ...]:
    frames: list[_MavlinkFrame] = []
    cursor = 0

    while cursor < len(data):
        remaining = len(data) - cursor
        if remaining < MAVLINK_V2_HEADER_LENGTH + MAVLINK_CHECKSUM_LENGTH:
            raise MavlinkDecodeError("MAVLink payload contains a truncated frame.")
        if data[cursor] != MAVLINK_V2_MAGIC:
            raise MavlinkDecodeError("MAVLink v2 magic byte was not found.")

        payload_length = data[cursor + 1]
        incompat_flags = data[cursor + 2]
        signed_length = (
            MAVLINK_SIGNATURE_LENGTH
            if incompat_flags & MAVLINK_SIGNED_INCOMPAT_FLAG
            else 0
        )
        frame_length = (
            MAVLINK_V2_HEADER_LENGTH
            + payload_length
            + MAVLINK_CHECKSUM_LENGTH
            + signed_length
        )
        if remaining < frame_length:
            raise MavlinkDecodeError("MAVLink payload contains an incomplete frame.")

        frame_data = data[cursor : cursor + frame_length]
        header = frame_data[:MAVLINK_V2_HEADER_LENGTH]
        payload = frame_data[
            MAVLINK_V2_HEADER_LENGTH : MAVLINK_V2_HEADER_LENGTH + payload_length
        ]
        checksum = frame_data[
            MAVLINK_V2_HEADER_LENGTH + payload_length :
            MAVLINK_V2_HEADER_LENGTH + payload_length + MAVLINK_CHECKSUM_LENGTH
        ]
        message_id = header[7] | (header[8] << 8) | (header[9] << 16)

        _validate_crc(header, payload, checksum, message_id)
        frames.append(
            _MavlinkFrame(
                system_id=header[5],
                component_id=header[6],
                message_id=message_id,
                payload=payload,
            )
        )
        cursor += frame_length

    return tuple(frames)


def _validate_crc(
    header: bytes,
    payload: bytes,
    checksum: bytes,
    message_id: int,
) -> None:
    crc_extra = CRC_EXTRAS.get(message_id)
    if crc_extra is None:
        return

    expected_crc = struct.unpack("<H", checksum)[0]
    actual_crc = _x25_crc(header[1:] + payload + bytes([crc_extra]))
    if actual_crc != expected_crc:
        raise MavlinkDecodeError(
            f"MAVLink frame {message_id} has invalid checksum."
        )


def _apply_heartbeat(payload: bytes, values: dict[str, Any]) -> None:
    payload = _coerce_payload_length(payload, 9, HEARTBEAT_MSG_ID)
    custom_mode, _, _, base_mode, system_status, _ = struct.unpack("<IBBBBB", payload)

    values["flight_mode"] = _flight_mode(custom_mode)
    values["armed"] = bool(base_mode & MAV_MODE_FLAG_SAFETY_ARMED)
    values["system_status"] = _system_status(system_status)


def _apply_attitude(payload: bytes, values: dict[str, Any]) -> None:
    payload = _coerce_payload_length(payload, 28, ATTITUDE_MSG_ID)
    time_boot_ms, roll, pitch, yaw, roll_speed, pitch_speed, yaw_speed = struct.unpack(
        "<Iffffff",
        payload,
    )

    values["_time_boot_ms"] = time_boot_ms
    values["roll_rad"] = roll
    values["pitch_rad"] = pitch
    values["yaw_rad"] = yaw
    values["roll_rate_rad_s"] = roll_speed
    values["pitch_rate_rad_s"] = pitch_speed
    values["yaw_rate_rad_s"] = yaw_speed


def _apply_global_position_int(payload: bytes, values: dict[str, Any]) -> None:
    payload = _coerce_payload_length(payload, 28, GLOBAL_POSITION_INT_MSG_ID)
    time_boot_ms, lat, lon, altitude, relative_altitude, vx, vy, vz, heading = struct.unpack(
        "<IiiiihhhH",
        payload,
    )

    values["_time_boot_ms"] = time_boot_ms
    values["latitude_deg"] = lat / 10_000_000
    values["longitude_deg"] = lon / 10_000_000
    values["altitude_m"] = altitude / 1000
    values["relative_altitude_m"] = relative_altitude / 1000
    values["velocity_x_m_s"] = vx / 100
    values["velocity_y_m_s"] = vy / 100
    values["velocity_z_m_s"] = -vz / 100
    values["vertical_speed_m_s"] = -vz / 100
    values["ground_speed_m_s"] = math.hypot(vx, vy) / 100
    if heading != 65535:
        values["heading_deg"] = heading / 100


def _apply_gps_raw_int(payload: bytes, values: dict[str, Any]) -> None:
    payload = _coerce_payload_length(payload, 30, GPS_RAW_INT_MSG_ID)
    timestamp_usec, lat, lon, altitude, eph, epv, speed, heading, fix_type, satellites = (
        struct.unpack("<QiiiHHHHBB", payload)
    )

    values["timestamp"] = _gps_timestamp(timestamp_usec)
    values["latitude_deg"] = lat / 10_000_000
    values["longitude_deg"] = lon / 10_000_000
    values["altitude_m"] = altitude / 1000
    values["gps_eph"] = float(eph)
    values["gps_epv"] = float(epv)
    values["ground_speed_m_s"] = speed / 100
    if heading != 65535:
        values["heading_deg"] = heading / 100
    values["gps_fix_type"] = fix_type
    values["satellites"] = satellites
    values["satellites_visible"] = satellites


def _gps_timestamp(timestamp_usec: int) -> datetime:
    if timestamp_usec >= _MIN_UNIX_GPS_TIMESTAMP_US:
        return datetime.fromtimestamp(timestamp_usec / 1_000_000, UTC)
    return datetime.now(tz=UTC)


def _apply_sys_status(payload: bytes, values: dict[str, Any]) -> None:
    payload = _coerce_payload_length(payload, 31, SYS_STATUS_MSG_ID)
    (
        _sensor_present,
        _sensor_enabled,
        sensor_health,
        _load,
        voltage_mv,
        current_ca,
        *_,
        battery_remaining,
    ) = struct.unpack("<IIIHHhHHHHHHb", payload)

    values["sensor_health_flags"] = sensor_health
    values["battery_voltage_v"] = voltage_mv / 1000
    if current_ca >= 0:
        values["battery_current_a"] = current_ca / 100
    else:
        values.pop("battery_current_a", None)
    values["battery_percent"] = float(battery_remaining)


def _apply_snapshot_freshness(
    values: dict[str, Any],
    frames: tuple[_MavlinkFrame, ...],
) -> None:
    groups = {
        group
        for frame in frames
        if (group := _message_group(frame.message_id)) is not None
    }
    for group in groups:
        values[_age_field_name(group)] = 0
    values["message_quality"] = _message_quality(
        {
            group: 0
            for group in groups
        }
    )


def _apply_stream_freshness(
    values: dict[str, Any],
    updated_at_s: dict[str, float],
    now_s: float,
) -> None:
    age_by_group: dict[str, int] = {}
    for group in _MESSAGE_GROUPS:
        updated_at = updated_at_s.get(group)
        if updated_at is None:
            continue
        age_ms = max(0, int((now_s - updated_at) * 1000))
        age_by_group[group] = age_ms
        values[_age_field_name(group)] = age_ms

    values["message_quality"] = _message_quality(age_by_group)


def _message_group(message_id: int) -> str | None:
    if message_id == ATTITUDE_MSG_ID:
        return _ATTITUDE_GROUP
    if message_id == GLOBAL_POSITION_INT_MSG_ID:
        return _POSITION_GROUP
    if message_id == GPS_RAW_INT_MSG_ID:
        return _GPS_GROUP
    if message_id in (HEARTBEAT_MSG_ID, SYS_STATUS_MSG_ID):
        return _SYSTEM_GROUP
    return None


def _age_field_name(group: str) -> str:
    return f"{group}_age_ms"


def _message_quality(age_by_group: dict[str, int]) -> float:
    scores = []
    for group in _MESSAGE_GROUPS:
        age_ms = age_by_group.get(group)
        if age_ms is None:
            scores.append(0.0)
            continue

        max_age_ms = _GROUP_MAX_AGE_MS[group]
        if age_ms <= max_age_ms:
            scores.append(1.0)
        elif age_ms >= max_age_ms * 3:
            scores.append(0.0)
        else:
            scores.append(1.0 - (age_ms - max_age_ms) / (max_age_ms * 2))

    return round(sum(scores) / len(scores), 3)


def _build_unified_telemetry(values: dict[str, Any]) -> UnifiedTelemetryPayload:
    required = (
        "timestamp",
        "drone_id",
        "latitude_deg",
        "longitude_deg",
        "altitude_m",
        "battery_percent",
        "satellites",
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise MavlinkDecodeError(
            f"MAVLink telemetry is missing required fields: {missing}."
        )

    return UnifiedTelemetryPayload(
        timestamp=values["timestamp"],
        drone_id=values["drone_id"],
        latitude_deg=values["latitude_deg"],
        longitude_deg=values["longitude_deg"],
        altitude_m=values["altitude_m"],
        battery_percent=values["battery_percent"],
        satellites=values["satellites"],
        ground_speed_m_s=values.get("ground_speed_m_s"),
        vertical_speed_m_s=values.get("vertical_speed_m_s"),
        heading_deg=values.get("heading_deg"),
        relative_altitude_m=values.get("relative_altitude_m"),
        velocity_x_m_s=values.get("velocity_x_m_s"),
        velocity_y_m_s=values.get("velocity_y_m_s"),
        velocity_z_m_s=values.get("velocity_z_m_s"),
        roll_rad=values.get("roll_rad"),
        pitch_rad=values.get("pitch_rad"),
        yaw_rad=values.get("yaw_rad"),
        roll_rate_rad_s=values.get("roll_rate_rad_s"),
        pitch_rate_rad_s=values.get("pitch_rate_rad_s"),
        yaw_rate_rad_s=values.get("yaw_rate_rad_s"),
        satellites_visible=values.get("satellites_visible"),
        gps_fix_type=values.get("gps_fix_type"),
        gps_eph=values.get("gps_eph"),
        gps_epv=values.get("gps_epv"),
        battery_voltage_v=values.get("battery_voltage_v"),
        battery_current_a=values.get("battery_current_a"),
        system_status=values.get("system_status"),
        flight_mode=values.get("flight_mode"),
        armed=values.get("armed"),
        sensor_health_flags=values.get("sensor_health_flags"),
        attitude_age_ms=values.get("attitude_age_ms"),
        position_age_ms=values.get("position_age_ms"),
        gps_age_ms=values.get("gps_age_ms"),
        system_age_ms=values.get("system_age_ms"),
        message_quality=values.get("message_quality"),
    )


def _has_required_telemetry_fields(values: dict[str, Any]) -> bool:
    return all(
        key in values
        for key in (
            "timestamp",
            "drone_id",
            "latitude_deg",
            "longitude_deg",
            "altitude_m",
            "battery_percent",
            "satellites",
        )
    )


def _coerce_payload_length(
    payload: bytes,
    expected_length: int,
    message_id: int,
) -> bytes:
    if len(payload) >= expected_length:
        return payload[:expected_length]
    return payload.ljust(expected_length, b"\x00")


def _drone_id(system_id: int) -> str:
    return f"uav-{system_id:03d}"


def _flight_mode(custom_mode: int) -> str:
    mapping = {
        1: "manual",
        2: "stabilize",
        3: "alt_hold",
        4: "auto",
        5: "guided",
        6: "rtl",
        9: "land",
    }
    return mapping.get(custom_mode, "auto")


def _system_status(system_status: int) -> str:
    mapping = {
        0: "uninit",
        1: "boot",
        2: "calibrating",
        3: "standby",
        4: "active",
        5: "critical",
        6: "emergency",
        7: "poweroff",
        8: "flight_termination",
    }
    return mapping.get(system_status, "active")


def _x25_crc(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        tmp = byte ^ (crc & 0xFF)
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = (
            (crc >> 8)
            ^ (tmp << 8)
            ^ (tmp << 3)
            ^ (tmp >> 4)
        ) & 0xFFFF
    return crc


__all__ = [
    "MavlinkDecodeError",
    "MavlinkV2TelemetryDecoder",
    "MavlinkV2TelemetryStreamDecoder",
]
