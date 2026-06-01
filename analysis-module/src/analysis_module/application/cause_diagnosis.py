"""Probable-cause enrichment for aggregated anomaly results."""

from __future__ import annotations

from dataclasses import dataclass

from analysis_module.domain import AnomalySource, AnomalyType, DetectedAnomaly
from analysis_module.domain.anomalies import EvidenceValue


@dataclass(frozen=True, slots=True)
class CauseDiagnosis:
    """Diagnostic explanation attached to an aggregated anomaly."""

    probable_cause: str
    cause_confidence: float
    diagnostic_evidence: dict[str, EvidenceValue]
    recommended_action: str


@dataclass(frozen=True, slots=True)
class CauseDiagnosisLayer:
    """Maps detected anomaly types to probable operational causes."""

    def enrich(self, anomaly: DetectedAnomaly) -> DetectedAnomaly:
        diagnosis = self.diagnose(anomaly)
        return DetectedAnomaly(
            type=anomaly.type,
            severity=anomaly.severity,
            message=anomaly.message,
            confidence=anomaly.confidence,
            source=anomaly.source,
            detector_kind=anomaly.detector_kind,
            detector_name=anomaly.detector_name,
            model_name=anomaly.model_name,
            score=anomaly.score,
            affected_fields=anomaly.affected_fields,
            affected_parameters=anomaly.affected_parameters,
            evidence=anomaly.evidence,
            window_start=anomaly.window_start,
            window_end=anomaly.window_end,
            probable_cause=diagnosis.probable_cause,
            cause_confidence=diagnosis.cause_confidence,
            diagnostic_evidence=diagnosis.diagnostic_evidence,
            reasons=anomaly.reasons,
            recommended_action=diagnosis.recommended_action,
            sources=anomaly.sources,
        )

    def diagnose(self, anomaly: DetectedAnomaly) -> CauseDiagnosis:
        profile = _CAUSE_PROFILES.get(
            anomaly.type,
            _CAUSE_PROFILES[AnomalyType.ANOMALOUS_BEHAVIOR],
        )
        return CauseDiagnosis(
            probable_cause=profile.probable_cause,
            cause_confidence=_bounded_confidence(
                anomaly.cause_confidence
                if anomaly.cause_confidence is not None
                else anomaly.confidence
            ),
            diagnostic_evidence=_diagnostic_evidence(anomaly),
            recommended_action=(
                anomaly.recommended_action or profile.recommended_action
            ),
        )


@dataclass(frozen=True, slots=True)
class _CauseProfile:
    probable_cause: str
    recommended_action: str


_CAUSE_PROFILES = {
    AnomalyType.GPS_SIGNAL_LOSS: _CauseProfile(
        probable_cause="gps_loss",
        recommended_action=(
            "Check GPS receiver visibility and navigation fallback mode."
        ),
    ),
    AnomalyType.GPS_SPOOFING: _CauseProfile(
        probable_cause="gps_spoofing",
        recommended_action=(
            "Compare GPS position with inertial movement and trusted "
            "location sources."
        ),
    ),
    AnomalyType.IMU_SPIKE: _CauseProfile(
        probable_cause="imu_spike",
        recommended_action="Inspect attitude sensor data and vibration level.",
    ),
    AnomalyType.BATTERY_DROP: _CauseProfile(
        probable_cause="battery_drop",
        recommended_action="Check power telemetry and prepare failsafe handling.",
    ),
    AnomalyType.LOW_BATTERY: _CauseProfile(
        probable_cause="low_battery",
        recommended_action="Start return-to-home or landing procedure.",
    ),
    AnomalyType.IMPOSSIBLE_ALTITUDE: _CauseProfile(
        probable_cause="altitude_sensor_or_conversion_error",
        recommended_action=(
            "Validate altitude source, units, and sensor calibration."
        ),
    ),
    AnomalyType.TELEMETRY_FREEZE: _CauseProfile(
        probable_cause="telemetry_freeze",
        recommended_action="Check telemetry source heartbeat and packet timestamps.",
    ),
    AnomalyType.TELEMETRY_GAP: _CauseProfile(
        probable_cause="packet_loss",
        recommended_action="Inspect link quality and transport buffering.",
    ),
    AnomalyType.MOTION_INCONSISTENCY: _CauseProfile(
        probable_cause="motion_inconsistency",
        recommended_action="Compare position, velocity, heading, and speed channels.",
    ),
    AnomalyType.ANOMALOUS_BEHAVIOR: _CauseProfile(
        probable_cause="unknown_anomalous_behavior",
        recommended_action="Inspect model score, feature deviations, and raw telemetry.",
    ),
}


def _diagnostic_evidence(anomaly: DetectedAnomaly) -> dict[str, EvidenceValue]:
    if anomaly.diagnostic_evidence:
        evidence = dict(anomaly.diagnostic_evidence)
        if anomaly.reasons and "reasons" not in evidence:
            evidence["reasons"] = [
                reason.to_dict()
                for reason in anomaly.reasons
            ]
        return evidence

    detectors = _source_detectors(anomaly.sources)
    if not detectors:
        detectors = (anomaly.detector_name,)

    evidence: dict[str, EvidenceValue] = {
        "anomaly_type": anomaly.type.value,
        "detectors": list(detectors),
        "affected_parameters": list(anomaly.affected_parameters),
        "primary_evidence": anomaly.evidence,
    }
    if anomaly.reasons:
        evidence["reasons"] = [
            reason.to_dict()
            for reason in anomaly.reasons
        ]
    return evidence


def _source_detectors(sources: tuple[AnomalySource, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(source.detector for source in sources))


def _bounded_confidence(value: float) -> float:
    return min(1.0, max(0.0, value))
