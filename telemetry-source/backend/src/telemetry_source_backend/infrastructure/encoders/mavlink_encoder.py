"""MAVLink telemetry encoder adapter."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field

from telemetry_source_backend.domain.common.models import TelemetrySample

MAVLINK_V2_MAGIC = 0xFD

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

MAV_TYPE_QUADROTOR = 2
MAV_AUTOPILOT_PX4 = 12
MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1
MAV_MODE_FLAG_SAFETY_ARMED = 128

MAVLINK_STREAM_MESSAGE_IDS = (
    HEARTBEAT_MSG_ID,
    ATTITUDE_MSG_ID,
    GLOBAL_POSITION_INT_MSG_ID,
    GPS_RAW_INT_MSG_ID,
    SYS_STATUS_MSG_ID,
)


@dataclass(frozen=True, slots=True)
class MavlinkStreamRateProfile:
    """Target rates for MAVLink messages in a continuous telemetry stream."""

    heartbeat_hz: float = 1.0
    sys_status_hz: float = 1.0
    gps_raw_int_hz: float = 5.0
    global_position_int_hz: float = 10.0
    attitude_hz: float = 50.0

    @property
    def max_rate_hz(self) -> float:
        return max(self.rates_by_message_id.values())

    @property
    def rates_by_message_id(self) -> dict[int, float]:
        return {
            HEARTBEAT_MSG_ID: self.heartbeat_hz,
            ATTITUDE_MSG_ID: self.attitude_hz,
            GLOBAL_POSITION_INT_MSG_ID: self.global_position_int_hz,
            GPS_RAW_INT_MSG_ID: self.gps_raw_int_hz,
            SYS_STATUS_MSG_ID: self.sys_status_hz,
        }


DEFAULT_MAVLINK_STREAM_RATE_PROFILE = MavlinkStreamRateProfile()


@dataclass(slots=True)
class MavlinkStreamRateScheduler:
    """Selects MAVLink messages that are due on each stream loop tick."""

    profile: MavlinkStreamRateProfile = DEFAULT_MAVLINK_STREAM_RATE_PROFILE
    elapsed_seconds: float = 0.0
    _last_sent_seconds: dict[int, float] = field(default_factory=dict)

    def due_message_ids(self, delta_seconds: float) -> tuple[int, ...]:
        message_ids: list[int] = []
        rates = self.profile.rates_by_message_id
        for message_id in MAVLINK_STREAM_MESSAGE_IDS:
            rate_hz = rates[message_id]
            interval_seconds = 1.0 / rate_hz
            last_sent_seconds = self._last_sent_seconds.get(message_id)
            if (
                last_sent_seconds is None
                or self.elapsed_seconds + 1e-9 >= last_sent_seconds + interval_seconds
            ):
                message_ids.append(message_id)
                self._last_sent_seconds[message_id] = self.elapsed_seconds

        self.elapsed_seconds += delta_seconds
        return tuple(message_ids)


@dataclass(slots=True)
class MavlinkTelemetryEncoder:
    """Encodes telemetry samples as a compact MAVLink telemetry subset."""

    system_id: int = 1
    component_id: int = 1
    sequence: int = field(default=0, init=False)

    def encode(self, sample: TelemetrySample) -> bytes:
        return b"".join(self.encode_messages(sample))

    def encode_messages(self, sample: TelemetrySample) -> tuple[bytes, ...]:
        return self.encode_messages_for_ids(sample, MAVLINK_STREAM_MESSAGE_IDS)

    def encode_messages_for_ids(
        self,
        sample: TelemetrySample,
        message_ids: tuple[int, ...],
    ) -> tuple[bytes, ...]:
        return tuple(self.encode_message(sample, message_id) for message_id in message_ids)

    def encode_message(self, sample: TelemetrySample, message_id: int) -> bytes:
        if message_id == HEARTBEAT_MSG_ID:
            return self._frame(
                message_id=HEARTBEAT_MSG_ID,
                payload=self._heartbeat_payload(sample),
                crc_extra=HEARTBEAT_CRC_EXTRA,
            )
        if message_id == ATTITUDE_MSG_ID:
            return self._frame(
                message_id=ATTITUDE_MSG_ID,
                payload=self._attitude_payload(sample),
                crc_extra=ATTITUDE_CRC_EXTRA,
            )
        if message_id == GLOBAL_POSITION_INT_MSG_ID:
            return self._frame(
                message_id=GLOBAL_POSITION_INT_MSG_ID,
                payload=self._global_position_int_payload(sample),
                crc_extra=GLOBAL_POSITION_INT_CRC_EXTRA,
            )
        if message_id == GPS_RAW_INT_MSG_ID:
            return self._frame(
                message_id=GPS_RAW_INT_MSG_ID,
                payload=self._gps_raw_int_payload(sample),
                crc_extra=GPS_RAW_INT_CRC_EXTRA,
            )
        if message_id == SYS_STATUS_MSG_ID:
            return self._frame(
                message_id=SYS_STATUS_MSG_ID,
                payload=self._sys_status_payload(sample),
                crc_extra=SYS_STATUS_CRC_EXTRA,
            )

        raise ValueError(f"Unsupported MAVLink message id: {message_id}")

    def _heartbeat_payload(self, sample: TelemetrySample) -> bytes:
        base_mode = MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        if sample.armed is not False:
            base_mode |= MAV_MODE_FLAG_SAFETY_ARMED

        return struct.pack(
            "<IBBBBB",
            _flight_mode_custom_mode(sample.flight_mode),
            MAV_TYPE_QUADROTOR,
            MAV_AUTOPILOT_PX4,
            base_mode,
            _system_status(sample.system_status),
            3,
        )

    def _attitude_payload(self, sample: TelemetrySample) -> bytes:
        return struct.pack(
            "<Iffffff",
            _time_boot_ms(sample),
            sample.roll_rad or 0.0,
            sample.pitch_rad or 0.0,
            sample.yaw_rad
            if sample.yaw_rad is not None
            else math.radians(sample.heading_deg or 0.0),
            sample.roll_rate_rad_s or 0.0,
            sample.pitch_rate_rad_s or 0.0,
            sample.yaw_rate_rad_s or 0.0,
        )

    def _global_position_int_payload(self, sample: TelemetrySample) -> bytes:
        altitude_mm = int(sample.altitude_m * 1000)
        relative_altitude_mm = int(
            (sample.relative_altitude_m if sample.relative_altitude_m is not None else sample.altitude_m)
            * 1000
        )
        speed_cm_s = int((sample.ground_speed_m_s or 0.0) * 100)
        heading_rad = math.radians(sample.heading_deg or 0.0)
        vx = int(
            (sample.velocity_x_m_s * 100)
            if sample.velocity_x_m_s is not None
            else speed_cm_s * math.cos(heading_rad)
        )
        vy = int(
            (sample.velocity_y_m_s * 100)
            if sample.velocity_y_m_s is not None
            else speed_cm_s * math.sin(heading_rad)
        )
        vz = int(
            -(
                sample.velocity_z_m_s
                if sample.velocity_z_m_s is not None
                else sample.vertical_speed_m_s or 0.0
            )
            * 100
        )
        heading_cdeg = (
            int((sample.heading_deg or 0.0) * 100) % 36000
            if sample.heading_deg is not None
            else 65535
        )

        return struct.pack(
            "<IiiiihhhH",
            _time_boot_ms(sample),
            int(sample.latitude_deg * 10_000_000),
            int(sample.longitude_deg * 10_000_000),
            altitude_mm,
            relative_altitude_mm,
            _int16(vx),
            _int16(vy),
            _int16(vz),
            heading_cdeg,
        )

    def _gps_raw_int_payload(self, sample: TelemetrySample) -> bytes:
        speed_cm_s = int((sample.ground_speed_m_s or 0.0) * 100)
        heading_cdeg = (
            int((sample.heading_deg or 0.0) * 100) % 36000
            if sample.heading_deg is not None
            else 65535
        )

        return struct.pack(
            "<QiiiHHHHBB",
            int(sample.timestamp.timestamp() * 1_000_000),
            int(sample.latitude_deg * 10_000_000),
            int(sample.longitude_deg * 10_000_000),
            int(sample.altitude_m * 1000),
            _uint16(int(sample.gps_eph if sample.gps_eph is not None else 100)),
            _uint16(int(sample.gps_epv if sample.gps_epv is not None else 150)),
            _uint16(speed_cm_s),
            _uint16(heading_cdeg),
            _uint8(sample.gps_fix_type if sample.gps_fix_type is not None else 3),
            _uint8(
                sample.satellites_visible
                if sample.satellites_visible is not None
                else sample.satellites
            ),
        )

    def _sys_status_payload(self, sample: TelemetrySample) -> bytes:
        sensor_flags = _uint32(
            sample.sensor_health_flags
            if sample.sensor_health_flags is not None
            else 0xFFFFFFFF
        )

        return struct.pack(
            "<IIIHHhHHHHHHb",
            sensor_flags,
            sensor_flags,
            sensor_flags,
            500,
            _uint16(int((sample.battery_voltage_v or 0.0) * 1000)),
            _int16(int((sample.battery_current_a or 0.0) * 100)),
            0,
            0,
            0,
            0,
            0,
            0,
            _int8(int(sample.battery_percent)),
        )

    def _frame(
        self,
        message_id: int,
        payload: bytes,
        crc_extra: int,
    ) -> bytes:
        header = bytes(
            [
                MAVLINK_V2_MAGIC,
                len(payload),
                0,
                0,
                self.sequence,
                self.system_id,
                self.component_id,
                message_id & 0xFF,
                (message_id >> 8) & 0xFF,
                (message_id >> 16) & 0xFF,
            ]
        )
        crc_input = header[1:] + payload + bytes([crc_extra])
        crc = _x25_crc(crc_input)
        self.sequence = (self.sequence + 1) % 256
        return header + payload + struct.pack("<H", crc)


def _time_boot_ms(sample: TelemetrySample) -> int:
    return int(sample.timestamp.timestamp() * 1000) & 0xFFFFFFFF


def _flight_mode_custom_mode(flight_mode: str | None) -> int:
    mapping = {
        "manual": 1,
        "stabilize": 2,
        "alt_hold": 3,
        "auto": 4,
        "guided": 5,
        "rtl": 6,
        "land": 9,
    }
    return mapping.get((flight_mode or "auto").lower(), 4)


def _system_status(system_status: str | None) -> int:
    mapping = {
        "uninit": 0,
        "boot": 1,
        "calibrating": 2,
        "standby": 3,
        "active": 4,
        "critical": 5,
        "emergency": 6,
        "poweroff": 7,
        "flight_termination": 8,
    }
    return mapping.get((system_status or "active").lower(), 4)


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


def _uint8(value: int) -> int:
    return max(min(value, 255), 0)


def _int8(value: int) -> int:
    return max(min(value, 127), -128)


def _uint16(value: int) -> int:
    return max(min(value, 65535), 0)


def _int16(value: int) -> int:
    return max(min(value, 32767), -32768)


def _uint32(value: int) -> int:
    return max(min(value, 0xFFFFFFFF), 0)
