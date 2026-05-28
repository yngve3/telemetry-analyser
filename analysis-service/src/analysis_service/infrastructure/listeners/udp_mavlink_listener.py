"""UDP MAVLink ingestion listener."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass

from analysis_service.application.ingestion import ListenerRecord
from analysis_service.application.sessions import SessionManager
from analysis_service.application.telemetry_mapping import (
    unified_telemetry_from_converter_payload,
)
from telemetry_converter import default_mavlink_stream_decoder


@dataclass(frozen=True, slots=True)
class UdpMavlinkListener:
    """Receives MAVLink packets over UDP and forwards telemetry to sessions."""

    async def run(
        self,
        record: ListenerRecord,
        session_manager: SessionManager,
    ) -> None:
        decoder = default_mavlink_stream_decoder()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((record.config.bind_host, record.config.bind_port))
            sock.settimeout(0.2)
            record.mark_active()

            while not record.stop_event.is_set():
                try:
                    payload, remote = await asyncio.to_thread(
                        sock.recvfrom,
                        record.config.buffer_size,
                    )
                except socket.timeout:
                    continue

                record.observe_packet(len(payload), remote)
                try:
                    converted = decoder.update(payload)
                except ValueError as exc:
                    record.observe_analysis_error(str(exc))
                    continue
                if converted is None:
                    continue

                telemetry = unified_telemetry_from_converter_payload(converted)
                try:
                    result = session_manager.analyze(
                        record.config.session_id,
                        telemetry,
                    )
                except Exception as exc:
                    record.observe_analysis_error(str(exc))
                    continue
                record.observe_result(result)
        except asyncio.CancelledError:
            raise
        except OSError as exc:
            record.mark_error(str(exc))
        finally:
            sock.close()
            record.mark_stopped()
