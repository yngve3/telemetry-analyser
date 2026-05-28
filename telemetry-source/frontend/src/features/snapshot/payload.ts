import type {
  SnapshotCreateRequest,
  SnapshotSampleRequest,
} from "../../shared/api/types";
import { isFiniteNumber, isPositive } from "../../shared/validation/forms";

export function buildSnapshotPayload(
  text: string,
  name: string,
  intervalSeconds: number,
  repeat: boolean,
): SnapshotCreateRequest {
  const parsed = JSON.parse(text) as
    | SnapshotSampleRequest[]
    | Partial<SnapshotCreateRequest>;

  const samples = Array.isArray(parsed) ? parsed : parsed.samples;
  if (!Array.isArray(samples)) {
    throw new Error("Snapshot JSON must contain a samples array.");
  }

  const payload: SnapshotCreateRequest = Array.isArray(parsed)
    ? {
        name,
        interval_seconds: intervalSeconds,
        repeat,
        samples,
      }
    : {
        name: parsed.name ?? name,
        interval_seconds: parsed.interval_seconds ?? intervalSeconds,
        repeat: parsed.repeat ?? repeat,
        samples,
      };

  validateSnapshotPayload(payload);
  return payload;
}

export function validateSnapshotPayload(payload: SnapshotCreateRequest): void {
  if (payload.name.trim().length === 0) {
    throw new Error("Snapshot name is required.");
  }

  if (!isPositive(payload.interval_seconds)) {
    throw new Error("Snapshot interval must be greater than zero.");
  }

  if (payload.samples.length === 0) {
    throw new Error("Snapshot must contain at least one sample.");
  }

  payload.samples.forEach((sample, index) => {
    validateSample(sample, index + 1);
  });
}

function validateSample(sample: SnapshotSampleRequest, index: number): void {
  if (typeof sample.timestamp !== "string" || sample.timestamp.trim().length === 0) {
    throw new Error(`Sample ${index}: timestamp is required.`);
  }
  if (typeof sample.drone_id !== "string" || sample.drone_id.trim().length === 0) {
    throw new Error(`Sample ${index}: drone_id is required.`);
  }
  requireFinite(sample.latitude_deg, index, "latitude_deg");
  requireFinite(sample.longitude_deg, index, "longitude_deg");
  requireFinite(sample.altitude_m, index, "altitude_m");
  requireFinite(sample.battery_percent, index, "battery_percent");
  requireFinite(sample.satellites, index, "satellites");
}

function requireFinite(
  value: number | null | undefined,
  sampleIndex: number,
  fieldName: string,
): void {
  if (!isFiniteNumber(value)) {
    throw new Error(`Sample ${sampleIndex}: ${fieldName} must be a number.`);
  }
}
