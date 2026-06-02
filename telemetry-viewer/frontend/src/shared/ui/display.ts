import type { DetectorResponse } from "../contracts/analysisProfile";

export type Translate = (key: string, fallback?: string) => string;

export const supportedAnalyzerNames = [
  "rule_based",
  "correlation_based",
  "isolation_forest",
  "autoencoder",
] as const;

const supportedAnalyzerOrder: Map<string, number> = new Map(
  supportedAnalyzerNames.map((name, index) => [name, index]),
);

export function isVisibleDetectorName(name: string): boolean {
  return supportedAnalyzerOrder.has(name);
}

export function visibleDetectors(detectors: DetectorResponse[]): DetectorResponse[] {
  return detectors
    .filter((detector) => isVisibleDetectorName(detector.name))
    .sort(
      (left, right) =>
        (supportedAnalyzerOrder.get(left.name) ?? Number.MAX_SAFE_INTEGER) -
        (supportedAnalyzerOrder.get(right.name) ?? Number.MAX_SAFE_INTEGER),
    );
}

export function formatDetectorName(name: string, t: Translate): string {
  return t(`detector.${name}`, humanizeIdentifier(name));
}

export function formatAnomalyType(type: string, t: Translate): string {
  return t(`anomalyType.${type}`, humanizeIdentifier(type));
}

export function formatCause(value: string, t: Translate): string {
  return t(`cause.${value}`, formatAnomalyType(value.toUpperCase(), t));
}

export function formatFieldName(name: string, t: Translate): string {
  return (
    t(`field.${name}`, "") ||
    t(`detector.${name}`, "") ||
    t(`anomalyType.${name}`, "") ||
    t(`cause.${name}`, "") ||
    humanizeIdentifier(name)
  );
}

export function formatDisplayValue(value: string, t: Translate): string {
  const message = formatMessage(value, t);
  if (message !== value) {
    return message;
  }
  const translated =
    t(`detector.${value}`, "") ||
    t(`anomalyType.${value}`, "") ||
    t(`cause.${value}`, "") ||
    t(`field.${value}`, "") ||
    t(`status.${value}`, "") ||
    t(`severity.${value}`, "");
  if (translated) {
    return translated;
  }
  if (looksTechnical(value)) {
    return humanizeIdentifier(value);
  }
  return value;
}

export function formatMessage(message: string, t: Translate): string {
  const lowBattery = /^Battery level is low: ([0-9.]+)%\.$/.exec(message);
  if (lowBattery) {
    return t("analysisMessage.lowBattery", "Battery level is low: {value}%.")
      .replace("{value}", lowBattery[1]);
  }

  const impossibleAltitude =
    /^Altitude is outside the physically expected range: ([0-9.-]+) m\.$/.exec(
      message,
    );
  if (impossibleAltitude) {
    return t(
      "analysisMessage.impossibleAltitude",
      "Altitude is outside the physically expected range: {value} m.",
    ).replace("{value}", impossibleAltitude[1]);
  }

  const key = messageKeys[message];
  return key ? t(key, message) : message;
}

export function normalizeDisplayValue(value: unknown, t: Translate): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeDisplayValue(item, t));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        formatFieldName(key, t),
        normalizeDisplayValue(item, t),
      ]),
    );
  }
  if (typeof value === "string") {
    return formatDisplayValue(value, t);
  }
  return value;
}

function looksTechnical(value: string): boolean {
  return (
    /^[A-Z0-9_]+$/.test(value) ||
    /^[a-z0-9]+(_[a-z0-9]+)+$/.test(value) ||
    /^[a-z]+(?:[A-Z][a-z0-9]+)+$/.test(value)
  );
}

function humanizeIdentifier(value: string): string {
  return value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .toLowerCase()
    .replace(/^./, (char) => char.toUpperCase());
}

const messageKeys: Record<string, string> = {
  "GPS signal is unavailable or below the required fix quality.":
    "analysisMessage.gpsSignalLoss",
  "GPS position changed faster than the reported motion allows.":
    "analysisMessage.gpsSpoofing",
  "IMU attitude or angular-rate data contains a sudden spike.":
    "analysisMessage.imuSpike",
  "Battery percentage dropped faster than expected.":
    "analysisMessage.batteryDrop",
  "Telemetry values did not change over the configured interval.":
    "analysisMessage.telemetryFreeze",
  "Telemetry stream has a larger than expected time gap.":
    "analysisMessage.telemetryGap",
  "Telemetry motion fields report inconsistent speeds.":
    "analysisMessage.motionInconsistency",
  "Telemetry channels describe inconsistent motion.":
    "analysisMessage.correlationMotion",
  "Battery percentage dropped without a matching voltage drop.":
    "analysisMessage.correlationBattery",
  "Telemetry freshness is below the adaptive correlation threshold.":
    "analysisMessage.adaptiveFreshness",
  "Telemetry parameters violate the adaptive consistency profile.":
    "analysisMessage.adaptiveConsistency",
  "Adaptive correlation profile is collecting normal telemetry.":
    "analysisMessage.adaptiveCollecting",
  "Feature reconstruction error exceeded the anomaly threshold.":
    "analysisMessage.autoencoder",
  "Isolation Forest score exceeded the anomaly threshold.":
    "analysisMessage.isolationForest",
  "Model score exceeded the configured anomaly threshold.":
    "analysisMessage.modelScore",
  "Check GPS receiver visibility and navigation fallback mode.":
    "analysisMessage.actionGpsSignalLoss",
  "Compare GPS position with inertial movement and trusted location sources.":
    "analysisMessage.actionGpsSpoofing",
  "Inspect attitude sensor data and vibration level.":
    "analysisMessage.actionImuSpike",
  "Check power telemetry and prepare failsafe handling.":
    "analysisMessage.actionBatteryDrop",
  "Start return-to-home or landing procedure.":
    "analysisMessage.actionLowBattery",
  "Validate altitude source, units, and sensor calibration.":
    "analysisMessage.actionImpossibleAltitude",
  "Check telemetry source heartbeat and packet timestamps.":
    "analysisMessage.actionTelemetryFreeze",
  "Inspect link quality and transport buffering.":
    "analysisMessage.actionTelemetryGap",
  "Compare position, velocity, heading, and speed channels.":
    "analysisMessage.actionMotionInconsistency",
  "Inspect model score, feature deviations, and raw telemetry.":
    "analysisMessage.actionAnomalousBehavior",
};
