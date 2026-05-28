import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import {
  Bug,
  Gauge,
  Pause,
  Play,
  Plus,
  Send,
  SkipForward,
  Square,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import {
  createSyntheticMission,
  getSyntheticMissionStatus,
  getSyntheticSample,
  getSyntheticSampleBatch,
  listSyntheticMissions,
  pauseSyntheticMission,
  resumeSyntheticMission,
  startSyntheticMission,
  startSyntheticUdpStream,
  stopSyntheticMission,
  submitSyntheticMissionCommand,
} from "../features/synthetic/api";
import {
  defaultStep,
  StepRow,
} from "../features/synthetic/components/StepRow";
import { validateMissionScript } from "../features/synthetic/validation";
import type {
  AnomalyType,
  MissionCommandRequest,
  MissionScriptRequest,
  MissionStatusResponse,
  ScriptHomeRequest,
  TelemetrySampleResponse,
  UdpStreamRequest,
  UdpStreamStatusResponse,
} from "../shared/api/types";
import { useI18n } from "../shared/i18n/I18nProvider";
import { EmptyState } from "../shared/ui/EmptyState";
import { JsonPreview } from "../shared/ui/JsonPreview";
import { StatusPill } from "../shared/ui/StatusPill";
import { isPositive, validateUdpTarget } from "../shared/validation/forms";

type MissionAction = "start" | "pause" | "resume" | "stop";

const missionActions: Record<
  MissionAction,
  (missionId: string) => Promise<MissionStatusResponse>
> = {
  start: startSyntheticMission,
  pause: pauseSyntheticMission,
  resume: resumeSyntheticMission,
  stop: stopSyntheticMission,
};

const initialMission: MissionScriptRequest = {
  name: "simple_mission",
  frequency_hz: 20,
  drone_id: "uav-001",
  home: {
    latitude: 47.397742,
    longitude: 8.545594,
    altitude: 0,
    heading_deg: 0,
    battery: 100,
  },
  steps: [
    defaultStep("takeoff"),
    defaultStep("move_forward"),
    defaultStep("turn"),
    defaultStep("hover"),
    defaultStep("return_home"),
    defaultStep("landing"),
  ],
  motion_profile: {
    horizontal_acceleration_m_s2: 2,
    default_climb_rate_m_s: 3,
    default_descent_rate_m_s: 2,
    default_yaw_rate_deg_s: 45,
    default_return_speed_m_s: 8,
  },
  noise_profile: {
    random_seed: null,
    gps_position_std_m: 0,
    altitude_std_m: 0,
    speed_std_m_s: 0,
    heading_std_deg: 0,
    battery_std_percent: 0,
  },
  battery_profile: {
    takeoff_percent_per_sec: 0.025,
    waypoint_percent_per_sec: 0.015,
    turn_percent_per_sec: 0.01,
    hover_percent_per_sec: 0.012,
    return_home_percent_per_sec: 0.015,
    landing_percent_per_sec: 0.01,
  },
};

const initialUdp: UdpStreamRequest = {
  host: "127.0.0.1",
  port: 14551,
  frequency_hz: 20,
};

const anomalyTypes: AnomalyType[] = [
  "GPS_SIGNAL_LOSS",
  "GPS_SPOOFING",
  "IMU_SPIKE",
  "MOTION_INCONSISTENCY",
  "BATTERY_DROP",
  "LOW_BATTERY",
  "TELEMETRY_FREEZE",
  "TELEMETRY_GAP",
  "IMPOSSIBLE_ALTITUDE",
  "ANOMALOUS_BEHAVIOR",
];

type RuntimeState = "running" | "paused" | "completed" | "idle";
type Translate = (key: string, fallback: string) => string;

export function SyntheticPage() {
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const [mission, setMission] = useState<MissionScriptRequest>(initialMission);
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);
  const [udp, setUdp] = useState<UdpStreamRequest>(initialUdp);
  const [sampleCount, setSampleCount] = useState(3);
  const [anomaly, setAnomaly] = useState({
    type: "GPS_SPOOFING" as AnomalyType,
    start_after_sec: 0,
    duration_sec: 5,
    intensity: 0.7,
  });
  const [targetSpeed, setTargetSpeed] = useState(8);
  const [missionError, setMissionError] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [telemetryError, setTelemetryError] = useState<string | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);

  const missionsQuery = useQuery({
    queryKey: ["synthetic-missions"],
    queryFn: listSyntheticMissions,
    refetchInterval: 2500,
  });
  const statusQuery = useQuery({
    queryKey: ["synthetic-mission", selectedMissionId],
    queryFn: () => getSyntheticMissionStatus(selectedMissionId as string),
    enabled: selectedMissionId !== null,
    refetchInterval: 1500,
  });

  const createMutation = useMutation({
    mutationFn: createSyntheticMission,
    onSuccess: (response) => {
      setSelectedMissionId(response.mission_id);
      return invalidateMissionQueries(queryClient, response.mission_id);
    },
  });
  const actionMutation = useMutation({
    mutationFn: ({
      missionId,
      action,
    }: {
      missionId: string;
      action: MissionAction;
    }) => missionActions[action](missionId),
    onSuccess: (response) => invalidateMissionQueries(queryClient, response.mission_id),
  });
  const sampleMutation = useMutation({
    mutationFn: (missionId: string) => getSyntheticSample(missionId),
  });
  const batchMutation = useMutation({
    mutationFn: (missionId: string) =>
      getSyntheticSampleBatch(missionId, sampleCount),
  });
  const streamMutation = useMutation({
    mutationFn: (missionId: string) => startSyntheticUdpStream(missionId, udp),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["synthetic-streams"] }),
  });
  const commandMutation = useMutation({
    mutationFn: ({
      missionId,
      payload,
    }: {
      missionId: string;
      payload: MissionCommandRequest;
    }) => submitSyntheticMissionCommand(missionId, payload),
    onSuccess: (response) => invalidateMissionQueries(queryClient, response.mission_id),
  });

  useEffect(() => {
    if (selectedMissionId === null && missionsQuery.data?.length) {
      setSelectedMissionId(missionsQuery.data[0].mission_id);
    }
  }, [selectedMissionId, missionsQuery.data]);

  function submitMission(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateMissionScript(mission);
    if (validationError !== null) {
      setMissionError(validationError);
      return;
    }

    setMissionError(null);
    createMutation.mutate(mission);
  }

  function updateHome(name: keyof ScriptHomeRequest, value: string) {
    setMission((current) => ({
      ...current,
      home: {
        ...current.home,
        [name]: Number(value),
      },
    }));
  }

  function runAction(action: MissionAction) {
    if (selectedMissionId) {
      actionMutation.mutate({ missionId: selectedMissionId, action });
    }
  }

  function submitAnomalyCommand() {
    if (!selectedMissionId) {
      return;
    }
    if (anomaly.start_after_sec < 0) {
      setCommandError(
        t(
          "validation.anomalyStartDelay",
          "Anomaly start delay must be greater than or equal to zero.",
        ),
      );
      return;
    }
    if (!isPositive(anomaly.duration_sec)) {
      setCommandError(
        t("validation.anomalyDuration", "Anomaly duration must be greater than zero."),
      );
      return;
    }
    if (!Number.isFinite(anomaly.intensity) || anomaly.intensity < 0) {
      setCommandError(
        t(
          "validation.anomalyIntensity",
          "Anomaly intensity must be greater than or equal to zero.",
        ),
      );
      return;
    }

    setCommandError(null);
    commandMutation.mutate({
      missionId: selectedMissionId,
      payload: {
        command: "inject_anomaly",
        ...anomaly,
      },
    });
  }

  function submitSpeedCommand() {
    if (!selectedMissionId) {
      return;
    }
    if (!isPositive(targetSpeed)) {
      setCommandError(
        t("validation.targetSpeed", "Target speed must be greater than zero."),
      );
      return;
    }

    setCommandError(null);
    commandMutation.mutate({
      missionId: selectedMissionId,
      payload: {
        command: "set_parameter",
        name: "target_speed",
        value: targetSpeed,
      },
    });
  }

  const selectedMissionRequired = selectedMissionId === null;

  function startStream() {
    if (!selectedMissionId) {
      return;
    }

    const validationError = validateUdpTarget(udp, {
      frequencyPositive: t(
        "validation.frequencyPositive",
        "Frequency must be greater than zero.",
      ),
      hostRequired: t("validation.hostRequired", "Host is required."),
      portInvalid: t(
        "validation.portRange",
        "Port must be an integer within [1, 65535].",
      ),
    });
    if (validationError !== null) {
      setStreamError(validationError);
      return;
    }

    setStreamError(null);
    streamMutation.mutate(selectedMissionId);
  }

  function getSampleBatch() {
    if (!selectedMissionId) {
      return;
    }

    if (!Number.isInteger(sampleCount) || sampleCount < 1 || sampleCount > 500) {
      setTelemetryError(
        t(
          "validation.batchCount",
          "Batch count must be an integer within [1, 500].",
        ),
      );
      return;
    }

    setTelemetryError(null);
    batchMutation.mutate(selectedMissionId);
  }

  function getSingleSample() {
    if (!selectedMissionId) {
      return;
    }

    setTelemetryError(null);
    sampleMutation.mutate(selectedMissionId);
  }

  const selectedMission = missionsQuery.data?.find(
    (item) => item.mission_id === selectedMissionId,
  );
  const selectedStatus = statusQuery.data;
  const runtimeState = getRuntimeState(selectedStatus);
  const primaryMissionAction = getPrimaryMissionAction(selectedStatus);
  const PrimaryMissionIcon = primaryMissionAction === "pause" ? Pause : Play;
  const progressPercent = getProgressPercent(selectedStatus);

  function runPrimaryAction() {
    runAction(primaryMissionAction);
  }

  return (
    <div className="synthetic-layout">
      <div className="page-stack">
        <section className="tool-panel">
          <div className="panel-header">
            <h2>{t("synthetic.createMission", "Create mission")}</h2>
          </div>

          <form onSubmit={submitMission}>
            <div className="form-grid">
              <label className="field">
                <span>{t("common.name", "Name")}</span>
                <input
                  required
                  value={mission.name}
                  onChange={(event) =>
                    setMission((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="field">
                <span>{t("synthetic.droneId", "Drone ID")}</span>
                <input
                  required
                  value={mission.drone_id}
                  onChange={(event) =>
                    setMission((current) => ({
                      ...current,
                      drone_id: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="field">
                <span>{t("common.frequencyHz", "Frequency, Hz")}</span>
                <input
                  min="0.001"
                  required
                  step="0.001"
                  type="number"
                  value={mission.frequency_hz}
                  onChange={(event) =>
                    setMission((current) => ({
                      ...current,
                      frequency_hz: Number(event.target.value),
                    }))
                  }
                />
              </label>
              <label className="field">
                <span>{t("synthetic.batteryPercent", "Battery, %")}</span>
                <input
                  min="0"
                  max="100"
                  type="number"
                  value={mission.home.battery}
                  onChange={(event) => updateHome("battery", event.target.value)}
                />
              </label>
              <label className="field">
                <span>{t("synthetic.latitude", "Latitude")}</span>
                <input
                  required
                  step="0.000001"
                  type="number"
                  value={mission.home.latitude}
                  onChange={(event) => updateHome("latitude", event.target.value)}
                />
              </label>
              <label className="field">
                <span>{t("synthetic.longitude", "Longitude")}</span>
                <input
                  required
                  step="0.000001"
                  type="number"
                  value={mission.home.longitude}
                  onChange={(event) => updateHome("longitude", event.target.value)}
                />
              </label>
              <label className="field">
                <span>{t("synthetic.altitudeM", "Altitude, m")}</span>
                <input
                  step="0.1"
                  type="number"
                  value={mission.home.altitude}
                  onChange={(event) => updateHome("altitude", event.target.value)}
                />
              </label>
              <label className="field">
                <span>{t("synthetic.headingDeg", "Heading, deg")}</span>
                <input
                  step="0.1"
                  type="number"
                  value={mission.home.heading_deg}
                  onChange={(event) => updateHome("heading_deg", event.target.value)}
                />
              </label>
            </div>

            <div className="step-list">
              {mission.steps.map((step, index) => (
                <StepRow
                  canRemove={mission.steps.length > 1}
                  index={index}
                  key={`${index}-${step.type}`}
                  step={step}
                  onChange={(nextStep) =>
                    setMission((current) => ({
                      ...current,
                      steps: current.steps.map((item, itemIndex) =>
                        itemIndex === index ? nextStep : item,
                      ),
                    }))
                  }
                  onRemove={() =>
                    setMission((current) => ({
                      ...current,
                      steps: current.steps.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                    }))
                  }
                />
              ))}
            </div>

            <div className="button-row">
              <button
                className="secondary-button"
                onClick={() =>
                  setMission((current) => ({
                    ...current,
                    steps: [...current.steps, defaultStep("hover")],
                  }))
                }
                type="button"
              >
                <Plus size={17} />
                {t("synthetic.addStep", "Add step")}
              </button>
              <button
                className="primary-button"
                disabled={createMutation.isPending}
                type="submit"
              >
                <Plus size={17} />
                {t("synthetic.createMission", "Create mission")}
              </button>
            </div>

            {createMutation.error ? (
              <div className="message error">{createMutation.error.message}</div>
            ) : null}
            {missionError ? <div className="message error">{missionError}</div> : null}
          </form>
        </section>

        <section className="data-panel">
          <div className="panel-header">
            <h2>{t("synthetic.missions", "Missions")}</h2>
            <StatusPill
              label={`${missionsQuery.data?.length ?? 0} ${t("synthetic.created", "created")}`}
              tone="neutral"
            />
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("common.name", "Name")}</th>
                  <th>{t("common.frequency", "Frequency")}</th>
                  <th>{t("common.status", "Status")}</th>
                </tr>
              </thead>
              <tbody>
                {missionsQuery.data?.map((item) => (
                  <tr
                    className={
                      item.mission_id === selectedMissionId ? "selected-row" : undefined
                    }
                    key={item.mission_id}
                  >
                    <td>
                      <button
                        className="mission-select-button"
                        onClick={() => setSelectedMissionId(item.mission_id)}
                        type="button"
                      >
                        {item.name}
                      </button>
                    </td>
                    <td>{item.frequency_hz} Hz</td>
                    <td>
                      <StatusPill
                        label={
                          item.is_completed
                            ? t("common.completed", "completed")
                            : item.is_running
                              ? t("common.running", "running")
                              : t("common.idle", "idle")
                        }
                        tone={
                          item.is_completed
                            ? "neutral"
                            : item.is_running
                              ? "success"
                              : "warning"
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {missionsQuery.data?.length === 0 ? (
            <EmptyState label={t("synthetic.noMissions", "No missions")} />
          ) : null}
        </section>
      </div>

      <div className="page-stack">
        <section className="tool-panel mission-control-panel">
          <div className="panel-header">
            <div>
              <h2>{t("synthetic.selectedMission", "Selected mission")}</h2>
              <span className="panel-subtitle">
                {selectedStatus?.name ??
                  selectedMission?.name ??
                  t("synthetic.noMissionSelected", "No mission selected")}
              </span>
            </div>
            {selectedStatus ? (
              <StatusPill
                label={getRuntimeStateLabel(runtimeState, t)}
                tone={getRuntimeStateTone(runtimeState)}
              />
            ) : null}
          </div>

          {selectedStatus ? (
            <>
              <div className="mission-progress">
                <div className="mission-progress-label">
                  <span>{t("synthetic.progress", "Progress")}</span>
                  <strong>{Math.round(progressPercent)}%</strong>
                </div>
                <div className="progress-track" aria-hidden="true">
                  <span style={{ width: `${progressPercent}%` }} />
                </div>
              </div>

              <div className="metric-grid">
                <Metric
                  label={t("synthetic.elapsed", "Elapsed")}
                  value={`${selectedStatus.elapsed_sec.toFixed(1)} s`}
                />
                <Metric
                  label={t("synthetic.duration", "Duration")}
                  value={`${selectedStatus.total_duration_sec.toFixed(1)} s`}
                />
                <Metric
                  label={t("synthetic.phase", "Phase")}
                  value={selectedStatus.active_phase_index}
                />
                <Metric
                  label={t("synthetic.anomalies", "Anomalies")}
                  value={selectedStatus.scheduled_anomalies_count}
                />
              </div>
            </>
          ) : (
            <EmptyState label={t("synthetic.selectMissionHint", "Select a mission from the list")} />
          )}

          <div className="button-row mission-actions">
            <button
              className="primary-button"
              disabled={selectedMissionRequired || actionMutation.isPending}
              onClick={runPrimaryAction}
              type="button"
            >
              <PrimaryMissionIcon size={16} />
              {getPrimaryMissionActionLabel(primaryMissionAction, t)}
            </button>
            <button
              className="danger-button"
              disabled={selectedMissionRequired || actionMutation.isPending}
              onClick={() => runAction("stop")}
              type="button"
            >
              <Square size={16} />
              {t("common.stop", "Stop")}
            </button>
          </div>

          {actionMutation.error ? (
            <div className="message error">{actionMutation.error.message}</div>
          ) : null}
        </section>

        <section className="tool-panel">
          <div className="panel-header">
            <h2>{t("synthetic.anomalyInjection", "Anomaly injection")}</h2>
            {selectedStatus?.is_running ? (
              <StatusPill label={t("common.active", "Active")} tone="success" />
            ) : null}
          </div>

          <div className="form-grid">
            <label className="field">
              <span>{t("synthetic.anomaly", "Anomaly")}</span>
              <select
                disabled={selectedMissionRequired}
                value={anomaly.type}
                onChange={(event) =>
                  setAnomaly((current) => ({
                    ...current,
                    type: event.target.value as AnomalyType,
                  }))
                }
              >
                {anomalyTypes.map((type) => (
                  <option key={type} value={type}>
                    {t(`anomaly.${type}`, type)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>{t("synthetic.startAfterSec", "Start after, sec")}</span>
              <input
                disabled={selectedMissionRequired}
                min="0"
                step="0.1"
                type="number"
                value={anomaly.start_after_sec}
                onChange={(event) =>
                  setAnomaly((current) => ({
                    ...current,
                    start_after_sec: Number(event.target.value),
                  }))
                }
              />
            </label>
            <label className="field">
              <span>{t("synthetic.durationSec", "Duration, sec")}</span>
              <input
                disabled={selectedMissionRequired}
                min="0.1"
                step="0.1"
                type="number"
                value={anomaly.duration_sec}
                onChange={(event) =>
                  setAnomaly((current) => ({
                    ...current,
                    duration_sec: Number(event.target.value),
                  }))
                }
              />
            </label>
            <label className="field">
              <span>{t("synthetic.intensity", "Intensity")}</span>
              <input
                disabled={selectedMissionRequired}
                min="0"
                step="0.1"
                type="number"
                value={anomaly.intensity}
                onChange={(event) =>
                  setAnomaly((current) => ({
                    ...current,
                    intensity: Number(event.target.value),
                  }))
                }
              />
            </label>
            <label className="field">
              <span>{t("synthetic.targetSpeed", "Target speed, m/s")}</span>
              <input
                disabled={selectedMissionRequired}
                min="0"
                step="0.1"
                type="number"
                value={targetSpeed}
                onChange={(event) => setTargetSpeed(Number(event.target.value))}
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={selectedMissionRequired || commandMutation.isPending}
              onClick={submitAnomalyCommand}
              type="button"
            >
              <Bug size={16} />
              {t("synthetic.injectAnomaly", "Inject anomaly")}
            </button>
            <button
              className="secondary-button"
              disabled={selectedMissionRequired || commandMutation.isPending}
              onClick={submitSpeedCommand}
              type="button"
            >
              <Gauge size={16} />
              {t("synthetic.setTargetSpeed", "Set target speed")}
            </button>
          </div>

          {commandMutation.error ? (
            <div className="message error">{commandMutation.error.message}</div>
          ) : null}
          {commandError ? <div className="message error">{commandError}</div> : null}
        </section>

        <section className="tool-panel">
          <div className="panel-header">
            <h2>{t("synthetic.udpStream", "UDP stream")}</h2>
          </div>

          <div className="form-grid">
            <label className="field">
              <span>{t("common.host", "Host")}</span>
              <input
                disabled={selectedMissionRequired}
                value={udp.host}
                onChange={(event) =>
                  setUdp((current) => ({ ...current, host: event.target.value }))
                }
              />
            </label>
            <label className="field">
              <span>{t("common.port", "Port")}</span>
              <input
                disabled={selectedMissionRequired}
                max="65535"
                min="1"
                type="number"
                value={udp.port}
                onChange={(event) =>
                  setUdp((current) => ({
                    ...current,
                    port: Number(event.target.value),
                  }))
                }
              />
            </label>
            <label className="field">
              <span>{t("common.frequencyHz", "Frequency, Hz")}</span>
              <input
                disabled={selectedMissionRequired}
                min="0.001"
                step="0.001"
                type="number"
                value={udp.frequency_hz ?? ""}
                onChange={(event) =>
                  setUdp((current) => ({
                    ...current,
                    frequency_hz:
                      event.target.value === "" ? null : Number(event.target.value),
                  }))
                }
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={selectedMissionRequired || streamMutation.isPending}
              onClick={startStream}
              type="button"
            >
              <Send size={16} />
              {t("synthetic.startUdpStream", "Start UDP stream")}
            </button>
          </div>

          {streamMutation.data ? (
            <StreamSummary stream={streamMutation.data} t={t} />
          ) : null}
          {streamMutation.error ? (
            <div className="message error">{streamMutation.error.message}</div>
          ) : null}
          {streamError ? <div className="message error">{streamError}</div> : null}
        </section>

        <section className="tool-panel">
          <div className="panel-header">
            <h2>{t("synthetic.telemetryPreview", "Telemetry preview")}</h2>
          </div>

          <div className="form-grid one-column">
            <label className="field">
              <span>{t("synthetic.batchCount", "Batch count")}</span>
              <input
                disabled={selectedMissionRequired}
                max="500"
                min="1"
                type="number"
                value={sampleCount}
                onChange={(event) => setSampleCount(Number(event.target.value))}
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="secondary-button"
              disabled={selectedMissionRequired || sampleMutation.isPending}
              onClick={getSingleSample}
              type="button"
            >
              <Gauge size={16} />
              {t("synthetic.getSample", "Get sample")}
            </button>
            <button
              className="secondary-button"
              disabled={selectedMissionRequired || batchMutation.isPending}
              onClick={getSampleBatch}
              type="button"
            >
              <SkipForward size={16} />
              {t("synthetic.getBatch", "Get batch")}
            </button>
          </div>

          <TelemetryPreview
            batch={batchMutation.data}
            sample={sampleMutation.data}
            t={t}
          />
          {sampleMutation.error ? (
            <div className="message error">{sampleMutation.error.message}</div>
          ) : null}
          {batchMutation.error ? (
            <div className="message error">{batchMutation.error.message}</div>
          ) : null}
          {telemetryError ? (
            <div className="message error">{telemetryError}</div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TelemetryPreview({
  batch,
  sample,
  t,
}: {
  batch?: TelemetrySampleResponse[];
  sample?: TelemetrySampleResponse;
  t: Translate;
}) {
  const hasBatch = !!batch?.length;
  const payload = hasBatch ? batch : sample;

  if (!payload) {
    return (
      <EmptyState
        label={t("synthetic.noTelemetryPreview", "No telemetry preview yet")}
      />
    );
  }

  if (hasBatch) {
    return (
      <div className="preview-stack">
        <div className="preview-heading">
          <strong>{t("synthetic.messageBatch", "Message batch")}</strong>
          <StatusPill
            label={`${t("synthetic.batchCount", "Batch count")}: ${batch.length}`}
            tone="neutral"
          />
        </div>

        <div className="batch-preview">
          <table className="data-table compact-table">
            <thead>
              <tr>
                <th>{t("synthetic.messageNumber", "#")}</th>
                <th>{t("common.timestamp", "Timestamp")}</th>
                <th>{t("synthetic.altitudeM", "Altitude, m")}</th>
                <th>{t("synthetic.groundSpeed", "Ground speed, m/s")}</th>
                <th>{t("synthetic.batteryPercent", "Battery, %")}</th>
              </tr>
            </thead>
            <tbody>
              {batch.map((item, index) => (
                <tr key={`${item.timestamp}-${index}`}>
                  <td>{index + 1}</td>
                  <td className="code-cell">{item.timestamp}</td>
                  <td>{formatNumber(item.altitude_m, 1)}</td>
                  <td>{formatNumber(item.ground_speed_m_s, 1)}</td>
                  <td>{formatNumber(item.battery_percent, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <details className="json-details">
          <summary>{t("synthetic.showJson", "Show JSON")}</summary>
          <JsonPreview value={payload} />
        </details>
      </div>
    );
  }

  if (!sample) {
    return (
      <EmptyState
        label={t("synthetic.noTelemetryPreview", "No telemetry preview yet")}
      />
    );
  }

  return (
    <div className="preview-stack">
      <div className="preview-heading">
        <strong>{t("synthetic.telemetryMessage", "Telemetry message")}</strong>
        <StatusPill
          label={t("synthetic.singleMessage", "Single message")}
          tone="neutral"
        />
      </div>

      <div className="metric-grid">
        <Metric label={t("synthetic.droneId", "Drone ID")} value={sample.drone_id} />
        <Metric
          label={t("synthetic.position", "Position")}
          value={`${formatNumber(sample.latitude_deg, 6)}, ${formatNumber(sample.longitude_deg, 6)}`}
        />
        <Metric
          label={t("synthetic.altitudeM", "Altitude, m")}
          value={formatNumber(sample.altitude_m, 1)}
        />
        <Metric
          label={t("synthetic.groundSpeed", "Ground speed, m/s")}
          value={formatNumber(sample.ground_speed_m_s, 1)}
        />
        <Metric
          label={t("synthetic.batteryPercent", "Battery, %")}
          value={formatNumber(sample.battery_percent, 0)}
        />
        <Metric
          label={t("synthetic.satellites", "Satellites")}
          value={sample.satellites}
        />
        <Metric
          label={t("synthetic.headingDeg", "Heading, deg")}
          value={formatNumber(sample.heading_deg, 0)}
        />
        <Metric
          label={t("common.timestamp", "Timestamp")}
          value={sample.timestamp}
        />
      </div>

      <details className="json-details">
        <summary>{t("synthetic.showJson", "Show JSON")}</summary>
        <JsonPreview value={payload} />
      </details>
    </div>
  );
}

function StreamSummary({
  stream,
  t,
}: {
  stream: UdpStreamStatusResponse;
  t: Translate;
}) {
  return (
    <div className="preview-stack">
      <div className="preview-heading">
        <strong>{t("synthetic.streamStarted", "UDP stream started")}</strong>
        <StatusPill
          label={stream.is_active ? t("common.active", "Active") : t("common.inactive", "Inactive")}
          tone={stream.is_active ? "success" : "neutral"}
        />
      </div>

      <div className="metric-grid">
        <Metric
          label={t("common.endpoint", "Endpoint")}
          value={`${stream.host}:${stream.port}`}
        />
        <Metric
          label={t("common.frequencyHz", "Frequency, Hz")}
          value={stream.frequency_hz}
        />
        <Metric label={t("common.sent", "Sent")} value={stream.sent_count} />
        <Metric label={t("common.stream", "Stream")} value={stream.stream_id} />
      </div>

      <details className="json-details">
        <summary>{t("synthetic.showJson", "Show JSON")}</summary>
        <JsonPreview value={stream} />
      </details>
    </div>
  );
}

function getRuntimeState(status?: MissionStatusResponse): RuntimeState {
  if (!status) {
    return "idle";
  }
  if (status.is_completed) {
    return "completed";
  }
  if (status.is_running) {
    return "running";
  }
  if (status.elapsed_sec > 0) {
    return "paused";
  }
  return "idle";
}

function getRuntimeStateLabel(state: RuntimeState, t: Translate): string {
  switch (state) {
    case "running":
      return t("common.running", "running");
    case "paused":
      return t("common.paused", "paused");
    case "completed":
      return t("common.completed", "completed");
    case "idle":
      return t("common.idle", "idle");
  }
}

function getRuntimeStateTone(
  state: RuntimeState,
): "success" | "warning" | "neutral" {
  switch (state) {
    case "running":
      return "success";
    case "paused":
      return "warning";
    case "completed":
    case "idle":
      return "neutral";
  }
}

function getPrimaryMissionAction(status?: MissionStatusResponse): MissionAction {
  if (status?.is_running) {
    return "pause";
  }
  if (status && status.elapsed_sec > 0 && !status.is_completed) {
    return "resume";
  }
  return "start";
}

function getPrimaryMissionActionLabel(action: MissionAction, t: Translate): string {
  switch (action) {
    case "pause":
      return t("common.pause", "Pause");
    case "resume":
      return t("common.resume", "Resume");
    case "start":
      return t("common.start", "Start");
    case "stop":
      return t("common.stop", "Stop");
  }
}

function getProgressPercent(status?: MissionStatusResponse): number {
  if (!status || status.total_duration_sec <= 0) {
    return 0;
  }
  return Math.min(100, Math.max(0, (status.elapsed_sec / status.total_duration_sec) * 100));
}

function formatNumber(value: number | null | undefined, digits: number): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return value.toFixed(digits);
}

function invalidateMissionQueries(
  queryClient: QueryClient,
  missionId: string,
) {
  void queryClient.invalidateQueries({ queryKey: ["synthetic-missions"] });
  void queryClient.invalidateQueries({ queryKey: ["synthetic-mission", missionId] });
}
