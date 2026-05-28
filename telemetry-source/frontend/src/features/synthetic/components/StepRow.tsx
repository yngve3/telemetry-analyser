import { Trash2 } from "lucide-react";

import type {
  ScriptStepRequest,
  ScriptStepType,
  TurnDirection,
} from "../../../shared/api/types";
import { useI18n } from "../../../shared/i18n/I18nProvider";

type StepRowProps = {
  step: ScriptStepRequest;
  index: number;
  canRemove: boolean;
  onChange: (step: ScriptStepRequest) => void;
  onRemove: () => void;
};

const stepTypes: ScriptStepType[] = [
  "takeoff",
  "move_forward",
  "turn",
  "hover",
  "return_home",
  "landing",
];

const directions: TurnDirection[] = ["left", "right"];

export function StepRow({
  step,
  index,
  canRemove,
  onChange,
  onRemove,
}: StepRowProps) {
  const { t } = useI18n();

  function setNumber(name: keyof ScriptStepRequest, value: string) {
    onChange({
      ...step,
      [name]: value === "" ? null : Number(value),
    });
  }

  function changeType(type: ScriptStepType) {
    onChange(defaultStep(type));
  }

  return (
    <div className="step-row">
      <span className="step-index">{index + 1}</span>

      <label className="field">
        <span>{t("step.type", "Type")}</span>
        <select
          value={step.type}
          onChange={(event) => changeType(event.target.value as ScriptStepType)}
        >
          {stepTypes.map((type) => (
            <option key={type} value={type}>
              {t(`step.${type}`, type)}
            </option>
          ))}
        </select>
      </label>

      {renderStepFields(step, setNumber, onChange, t)}

      <button
        className="icon-button"
        disabled={!canRemove}
        onClick={onRemove}
        title={t("step.remove", "Remove step")}
        type="button"
      >
        <Trash2 size={17} />
      </button>
    </div>
  );
}

export function defaultStep(type: ScriptStepType): ScriptStepRequest {
  switch (type) {
    case "takeoff":
      return { type, target_altitude: 30 };
    case "move_forward":
      return { type, distance_m: 100, speed_m_s: 8 };
    case "turn":
      return { type, direction: "right", angle_deg: 90 };
    case "hover":
      return { type, duration_sec: 10 };
    case "return_home":
      return { type, speed_m_s: 8 };
    case "landing":
      return { type };
  }
}

function renderStepFields(
  step: ScriptStepRequest,
  setNumber: (name: keyof ScriptStepRequest, value: string) => void,
  onChange: (step: ScriptStepRequest) => void,
  t: (key: string, fallback?: string) => string,
) {
  switch (step.type) {
    case "takeoff":
      return (
        <>
          {numberField(t("synthetic.altitudeM", "Altitude, m"), step.target_altitude, (value) =>
            setNumber("target_altitude", value),
          )}
          {placeholderField(t)}
          {placeholderField(t)}
        </>
      );
    case "move_forward":
      return (
        <>
          {numberField(t("step.distanceM", "Distance, m"), step.distance_m, (value) =>
            setNumber("distance_m", value),
          )}
          {numberField(t("step.speedMs", "Speed, m/s"), step.speed_m_s, (value) =>
            setNumber("speed_m_s", value),
          )}
          {placeholderField(t)}
        </>
      );
    case "turn":
      return (
        <>
          <label className="field">
            <span>{t("step.direction", "Direction")}</span>
            <select
              value={step.direction ?? "right"}
              onChange={(event) =>
                onChange({
                  ...step,
                  direction: event.target.value as TurnDirection,
                })
              }
            >
              {directions.map((direction) => (
                <option key={direction} value={direction}>
                  {t(`step.${direction}`, direction)}
                </option>
              ))}
            </select>
          </label>
          {numberField(t("step.angleDeg", "Angle, deg"), step.angle_deg, (value) =>
            setNumber("angle_deg", value),
          )}
          {placeholderField(t)}
        </>
      );
    case "hover":
      return (
        <>
          {numberField(t("step.durationSec", "Duration, sec"), step.duration_sec, (value) =>
            setNumber("duration_sec", value),
          )}
          {placeholderField(t)}
          {placeholderField(t)}
        </>
      );
    case "return_home":
      return (
        <>
          {numberField(t("step.speedMs", "Speed, m/s"), step.speed_m_s, (value) =>
            setNumber("speed_m_s", value),
          )}
          {placeholderField(t)}
          {placeholderField(t)}
        </>
      );
    case "landing":
      return (
        <>
          {placeholderField(t)}
          {placeholderField(t)}
          {placeholderField(t)}
        </>
      );
  }
}

function numberField(
  label: string,
  value: number | null | undefined,
  onChange: (value: string) => void,
) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        min="0"
        step="0.1"
        type="number"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function placeholderField(t: (key: string, fallback?: string) => string) {
  return (
    <label className="field hidden-field" aria-hidden="true">
      <span>{t("step.unused", "Unused")}</span>
      <input tabIndex={-1} type="text" />
    </label>
  );
}
