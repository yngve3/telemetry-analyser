import type { UdpStreamRequest } from "../api/types";

type UdpTargetValidationMessages = {
  frequencyPositive?: string;
  hostRequired?: string;
  portInvalid?: string;
};

const DEFAULT_FREQUENCY_POSITIVE = "Frequency must be greater than zero.";
const DEFAULT_HOST_REQUIRED = "Host is required.";
const DEFAULT_PORT_INVALID = "Port must be an integer within [1, 65535].";

export function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function isPositive(value: number | null | undefined): value is number {
  return isFiniteNumber(value) && value > 0;
}

export function validatePort(
  port: number,
  message = DEFAULT_PORT_INVALID,
): string | null {
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    return message;
  }
  return null;
}

export function validateUdpTarget(
  request: UdpStreamRequest,
  messages: UdpTargetValidationMessages = {},
): string | null {
  if (request.host.trim().length === 0) {
    return messages.hostRequired ?? DEFAULT_HOST_REQUIRED;
  }

  const portError = validatePort(request.port, messages.portInvalid);
  if (portError !== null) {
    return portError;
  }

  if (request.frequency_hz !== undefined && request.frequency_hz !== null) {
    if (!isPositive(request.frequency_hz)) {
      return messages.frequencyPositive ?? DEFAULT_FREQUENCY_POSITIVE;
    }
  }

  return null;
}
