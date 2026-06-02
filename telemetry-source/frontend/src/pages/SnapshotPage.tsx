import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileJson, Play, Send, Square, Upload } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  createSnapshot,
  getSnapshotSamples,
  listSnapshots,
  sendSnapshotOnceUdp,
  startSnapshotUdpStream,
} from "../features/snapshot/api";
import { buildSnapshotPayload } from "../features/snapshot/payload";
import { stopSnapshotUdpStream } from "../features/streams/api";
import type {
  SnapshotCreateRequest,
  UdpStreamRequest,
} from "../shared/api/types";
import { useI18n } from "../shared/i18n/I18nProvider";
import { EmptyState } from "../shared/ui/EmptyState";
import { JsonPreview } from "../shared/ui/JsonPreview";
import { StatusPill } from "../shared/ui/StatusPill";
import { validateUdpTarget } from "../shared/validation/forms";

const samplePayload: SnapshotCreateRequest = {
  name: "short_snapshot",
  interval_seconds: 0.1,
  repeat: false,
  samples: [
    {
      timestamp: "2026-05-20T12:00:00+00:00",
      drone_id: "uav-001",
      latitude_deg: 47.397742,
      longitude_deg: 8.545594,
      altitude_m: 30,
      battery_percent: 90,
      satellites: 10,
      ground_speed_m_s: 8,
      vertical_speed_m_s: 0,
      heading_deg: 90,
      relative_altitude_m: 30,
      roll_rad: 0,
      pitch_rad: 0,
      yaw_rad: 1.5708,
      satellites_visible: 10,
      gps_fix_type: 3,
      gps_eph: 100,
      gps_epv: 150,
      battery_voltage_v: 12.2,
      battery_current_a: 8,
      system_status: "active",
      flight_mode: "auto",
      armed: true,
      sensor_health_flags: 4294967295,
    },
    {
      timestamp: "2026-05-20T12:00:01+00:00",
      drone_id: "uav-001",
      latitude_deg: 47.397742,
      longitude_deg: 8.545594,
      altitude_m: 31,
      battery_percent: 89.8,
      satellites: 10,
      ground_speed_m_s: 8,
      vertical_speed_m_s: 0,
      heading_deg: 90,
      relative_altitude_m: 31,
      roll_rad: 0,
      pitch_rad: 0,
      yaw_rad: 1.5708,
      satellites_visible: 10,
      gps_fix_type: 3,
      gps_eph: 100,
      gps_epv: 150,
      battery_voltage_v: 12.1,
      battery_current_a: 8.1,
      system_status: "active",
      flight_mode: "auto",
      armed: true,
      sensor_health_flags: 4294967295,
    },
  ],
};

const initialUdp: UdpStreamRequest = {
  host: "analysis-service",
  port: 14560,
  frequency_hz: 10,
  repeat: true,
};

export function SnapshotPage() {
  const queryClient = useQueryClient();
  const { t, tp } = useI18n();
  const [snapshotText, setSnapshotText] = useState(
    JSON.stringify(samplePayload, null, 2),
  );
  const [snapshotName, setSnapshotName] = useState(samplePayload.name);
  const [intervalSeconds, setIntervalSeconds] = useState(
    samplePayload.interval_seconds,
  );
  const [repeat, setRepeat] = useState(samplePayload.repeat);
  const [udp, setUdp] = useState<UdpStreamRequest>(initialUdp);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [udpError, setUdpError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const snapshotsQuery = useQuery({
    queryKey: ["snapshots"],
    queryFn: listSnapshots,
    refetchInterval: 2500,
  });
  const samplesQuery = useQuery({
    queryKey: ["snapshot-samples", selectedSnapshotId],
    queryFn: () => getSnapshotSamples(selectedSnapshotId as string),
    enabled: selectedSnapshotId !== null,
  });

  const preview = useMemo(() => {
    try {
      return { payload: buildSnapshotPayload(snapshotText, snapshotName, intervalSeconds, repeat) };
    } catch (error) {
      return { error: error instanceof Error ? error.message : String(error) };
    }
  }, [snapshotText, snapshotName, intervalSeconds, repeat]);

  const createMutation = useMutation({
    mutationFn: createSnapshot,
    onSuccess: (response) => {
      setSelectedSnapshotId(response.snapshot_id);
      return queryClient.invalidateQueries({ queryKey: ["snapshots"] });
    },
  });
  const sendOnceMutation = useMutation({
    mutationFn: (snapshotId: string) => sendSnapshotOnceUdp(snapshotId, udp),
  });
  const replayMutation = useMutation({
    mutationFn: (snapshotId: string) => startSnapshotUdpStream(snapshotId, udp),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["snapshot-streams"] }),
  });
  const stopReplayMutation = useMutation({
    mutationFn: stopSnapshotUdpStream,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["snapshot-streams"] }),
  });

  useEffect(() => {
    if (selectedSnapshotId === null && snapshotsQuery.data?.length) {
      setSelectedSnapshotId(snapshotsQuery.data[0].snapshot_id);
    }
  }, [selectedSnapshotId, snapshotsQuery.data]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = buildSnapshotPayload(
        snapshotText,
        snapshotName,
        intervalSeconds,
        repeat,
      );
      setParseError(null);
      createMutation.mutate(payload);
    } catch (error) {
      setParseError(error instanceof Error ? error.message : String(error));
    }
  }

  async function readFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setFileName(file.name);
    setSnapshotText(await file.text());
  }

  const activeReplayStreamId = replayMutation.data?.is_active
    ? replayMutation.data.stream_id
    : null;
  const previewPayload = "payload" in preview ? preview.payload : null;

  function sendOnce() {
    if (selectedSnapshotId === null) {
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
      setUdpError(validationError);
      return;
    }

    setUdpError(null);
    sendOnceMutation.mutate(selectedSnapshotId);
  }

  function replayStream() {
    if (selectedSnapshotId === null) {
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
      setUdpError(validationError);
      return;
    }

    setUdpError(null);
    replayMutation.mutate(selectedSnapshotId);
  }

  return (
    <div className="page-grid">
      <section className="tool-panel">
        <div className="panel-header">
          <h2>{t("snapshot.createSnapshot", "Create snapshot")}</h2>
          <StatusPill
            label={
              previewPayload
                ? tp("snapshot.sampleCount", previewPayload.samples.length)
                : t("common.invalid", "invalid")
            }
            tone={previewPayload ? "success" : "danger"}
          />
        </div>

        <form onSubmit={submit}>
          <div className="form-grid">
            <label className="field">
              <span>{t("common.name", "Name")}</span>
              <input
                required
                value={snapshotName}
                onChange={(event) => setSnapshotName(event.target.value)}
              />
            </label>
            <label className="field">
              <span>{t("snapshot.intervalSec", "Interval, sec")}</span>
              <input
                min="0.001"
                step="0.001"
                type="number"
                value={intervalSeconds}
                onChange={(event) => setIntervalSeconds(Number(event.target.value))}
              />
            </label>
            <label className="field checkbox-field">
              <input
                checked={repeat}
                type="checkbox"
                onChange={(event) => setRepeat(event.target.checked)}
              />
              <span>{t("snapshot.repeat", "Repeat")}</span>
            </label>
            <label className="field file-field">
              <span>{t("snapshot.jsonFile", "JSON file")}</span>
              <span className="file-picker">
                <span className="file-button">{t("common.chooseFile", "Choose file")}</span>
                <span className="file-name">
                  {fileName ?? t("common.noFileSelected", "No file selected")}
                </span>
                <input
                  className="file-input"
                  type="file"
                  accept="application/json,.json"
                  onChange={(event) => void readFile(event.target.files?.[0])}
                />
              </span>
            </label>
          </div>

          <label className="field">
            <span>{t("snapshot.snapshotJson", "Snapshot JSON")}</span>
            <textarea
              spellCheck={false}
              value={snapshotText}
              onChange={(event) => setSnapshotText(event.target.value)}
            />
          </label>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={createMutation.isPending}
              type="submit"
            >
              <Upload size={17} />
              {t("snapshot.createSnapshot", "Create snapshot")}
            </button>
          </div>

          {parseError ? <div className="message error">{parseError}</div> : null}
          {createMutation.error ? (
            <div className="message error">{createMutation.error.message}</div>
          ) : null}
        </form>
      </section>

      <div className="page-stack">
        <section className="data-panel">
          <div className="panel-header">
            <h2>{t("snapshot.snapshots", "Snapshots")}</h2>
            <StatusPill
              label={`${snapshotsQuery.data?.length ?? 0} ${t("snapshot.uploaded", "uploaded")}`}
              tone="neutral"
            />
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("common.name", "Name")}</th>
                  <th>{t("common.samples", "Samples")}</th>
                  <th>ID</th>
                </tr>
              </thead>
              <tbody>
                {snapshotsQuery.data?.map((snapshot) => (
                  <tr key={snapshot.snapshot_id}>
                    <td>
                      <button
                        className="ghost-button"
                        onClick={() => setSelectedSnapshotId(snapshot.snapshot_id)}
                        type="button"
                      >
                        {snapshot.name}
                      </button>
                    </td>
                    <td>{snapshot.samples_count}</td>
                    <td>{snapshot.snapshot_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {snapshotsQuery.data?.length === 0 ? (
            <EmptyState label={t("snapshot.noSnapshots", "No snapshots")} />
          ) : null}
        </section>

        <section className="tool-panel">
          <div className="panel-header">
            <h2>{t("snapshot.udpPublication", "UDP publication")}</h2>
          </div>

          <div className="form-grid">
            <label className="field">
              <span>{t("common.host", "Host")}</span>
              <input
                value={udp.host}
                onChange={(event) =>
                  setUdp((current) => ({ ...current, host: event.target.value }))
                }
              />
            </label>
            <label className="field">
              <span>{t("common.port", "Port")}</span>
              <input
                max="65535"
                min="1"
                type="number"
                value={udp.port}
                onChange={(event) =>
                  setUdp((current) => ({ ...current, port: Number(event.target.value) }))
                }
              />
            </label>
            <label className="field">
              <span>{t("common.frequencyHz", "Frequency, Hz")}</span>
              <input
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
            <label className="field checkbox-field">
              <input
                checked={udp.repeat ?? false}
                type="checkbox"
                onChange={(event) =>
                  setUdp((current) => ({ ...current, repeat: event.target.checked }))
                }
              />
              <span>{t("snapshot.repeatStream", "Repeat stream")}</span>
            </label>
          </div>

          <div className="button-row">
            <button
              className="secondary-button"
              disabled={selectedSnapshotId === null || sendOnceMutation.isPending}
              onClick={sendOnce}
              type="button"
            >
              <Send size={16} />
              {t("snapshot.sendOnce", "Send once")}
            </button>
            <button
              className="secondary-button"
              disabled={selectedSnapshotId === null || replayMutation.isPending}
              onClick={replayStream}
              type="button"
            >
              <Play size={16} />
              {t("snapshot.replayStream", "Replay stream")}
            </button>
            <button
              className="danger-button"
              disabled={activeReplayStreamId === null || stopReplayMutation.isPending}
              onClick={() =>
                activeReplayStreamId
                  ? stopReplayMutation.mutate(activeReplayStreamId)
                  : null
              }
              type="button"
            >
              <Square size={16} />
              {t("snapshot.stopStream", "Stop stream")}
            </button>
          </div>

          {sendOnceMutation.data ? <JsonPreview value={sendOnceMutation.data} /> : null}
          {replayMutation.data ? <JsonPreview value={replayMutation.data} /> : null}
          {sendOnceMutation.error ? (
            <div className="message error">{sendOnceMutation.error.message}</div>
          ) : null}
          {replayMutation.error ? (
            <div className="message error">{replayMutation.error.message}</div>
          ) : null}
          {stopReplayMutation.error ? (
            <div className="message error">{stopReplayMutation.error.message}</div>
          ) : null}
          {udpError ? <div className="message error">{udpError}</div> : null}
        </section>

        <section className="data-panel">
          <div className="panel-header">
            <h2>{t("common.samples", "Samples")}</h2>
            <FileJson size={18} />
          </div>
          {samplesQuery.data ? (
            <JsonPreview value={samplesQuery.data.samples.slice(0, 5)} />
          ) : (
            <EmptyState label={t("snapshot.noSnapshotSelected", "No snapshot selected")} />
          )}
        </section>
      </div>
    </div>
  );
}
