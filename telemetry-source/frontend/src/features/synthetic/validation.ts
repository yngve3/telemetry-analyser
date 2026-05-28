import type { MissionScriptRequest } from "../../shared/api/types";
import { isFiniteNumber, isPositive } from "../../shared/validation/forms";

export function validateMissionScript(payload: MissionScriptRequest): string | null {
  if (payload.name.trim().length === 0) {
    return "Mission name is required.";
  }

  if (payload.drone_id.trim().length === 0) {
    return "Drone ID is required.";
  }

  if (!isPositive(payload.frequency_hz)) {
    return "Mission frequency must be greater than zero.";
  }

  if (!isFiniteNumber(payload.home.latitude) || payload.home.latitude < -90 || payload.home.latitude > 90) {
    return "Home latitude must be within [-90, 90].";
  }

  if (!isFiniteNumber(payload.home.longitude) || payload.home.longitude < -180 || payload.home.longitude > 180) {
    return "Home longitude must be within [-180, 180].";
  }

  if (!isFiniteNumber(payload.home.battery) || payload.home.battery < 0 || payload.home.battery > 100) {
    return "Initial battery must be within [0, 100].";
  }

  if (payload.steps.length === 0) {
    return "Mission script must contain at least one step.";
  }

  for (let index = 0; index < payload.steps.length; index += 1) {
    const step = payload.steps[index];
    const stepNumber = index + 1;

    switch (step.type) {
      case "takeoff":
        if (!isPositive(step.target_altitude)) {
          return `Step ${stepNumber}: target_altitude must be greater than zero.`;
        }
        break;
      case "move_forward":
        if (!isPositive(step.distance_m)) {
          return `Step ${stepNumber}: distance_m must be greater than zero.`;
        }
        if (!isPositive(step.speed_m_s)) {
          return `Step ${stepNumber}: speed_m_s must be greater than zero.`;
        }
        break;
      case "turn":
        if (step.direction === undefined || step.direction === null) {
          return `Step ${stepNumber}: turn direction is required.`;
        }
        if (!isPositive(step.angle_deg)) {
          return `Step ${stepNumber}: angle_deg must be greater than zero.`;
        }
        break;
      case "hover":
        if (!isPositive(step.duration_sec)) {
          return `Step ${stepNumber}: duration_sec must be greater than zero.`;
        }
        break;
      case "return_home":
        if (step.speed_m_s !== undefined && step.speed_m_s !== null && !isPositive(step.speed_m_s)) {
          return `Step ${stepNumber}: speed_m_s must be greater than zero.`;
        }
        break;
      case "landing":
        break;
    }
  }

  return null;
}
