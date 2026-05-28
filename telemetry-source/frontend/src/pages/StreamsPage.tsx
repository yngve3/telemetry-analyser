import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, RefreshCw, Square } from "lucide-react";
import { useState } from "react";

import {
  getSnapshotUdpStreamPreview,
  getSyntheticUdpStreamPreview,
  listSnapshotUdpStreams,
  listSyntheticUdpStreams,
  stopSnapshotUdpStream,
  stopSyntheticUdpStream,
} from "../features/streams/api";
import type {
  SelectedStreamPreview,
  StreamPreviewResponse,
} from "../features/streams/types";
import {
  filterSnapshotStreams,
  filterSyntheticStreams,
  type StreamFilter,
} from "../features/streams/view";
import { useI18n } from "../shared/i18n/I18nProvider";
import { EmptyState } from "../shared/ui/EmptyState";
import { JsonPreview } from "../shared/ui/JsonPreview";
import { StatusPill } from "../shared/ui/StatusPill";

type Translate = (key: string, fallback: string) => string;

export function StreamsPage() {
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const [filter, setFilter] = useState<StreamFilter>("all");
  const [selectedPreview, setSelectedPreview] =
    useState<SelectedStreamPreview | null>(null);
  const syntheticQuery = useQuery({
    queryKey: ["synthetic-streams"],
    queryFn: listSyntheticUdpStreams,
    refetchInterval: 1500,
  });
  const snapshotQuery = useQuery({
    queryKey: ["snapshot-streams"],
    queryFn: listSnapshotUdpStreams,
    refetchInterval: 1500,
  });
  const previewQuery = useQuery({
    queryKey: ["stream-preview", selectedPreview],
    queryFn: () => {
      if (selectedPreview?.kind === "synthetic") {
        return getSyntheticUdpStreamPreview(selectedPreview.streamId);
      }
      if (selectedPreview?.kind === "snapshot") {
        return getSnapshotUdpStreamPreview(selectedPreview.streamId);
      }
      throw new Error("Stream preview is not selected.");
    },
    enabled: selectedPreview !== null,
    refetchInterval: selectedPreview !== null ? 1500 : false,
  });
  const stopSyntheticMutation = useMutation({
    mutationFn: stopSyntheticUdpStream,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["synthetic-streams"] });
      queryClient.invalidateQueries({ queryKey: ["stream-preview"] });
    },
  });
  const stopSnapshotMutation = useMutation({
    mutationFn: stopSnapshotUdpStream,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["snapshot-streams"] });
      queryClient.invalidateQueries({ queryKey: ["stream-preview"] });
    },
  });
  const syntheticStreams = filterSyntheticStreams(syntheticQuery.data, filter);
  const snapshotStreams = filterSnapshotStreams(snapshotQuery.data, filter);

  function refreshStreams() {
    void syntheticQuery.refetch();
    void snapshotQuery.refetch();
    void previewQuery.refetch();
  }

  return (
    <div className="page-stack">
      <section className="toolbar-panel">
        <div>
          <strong>{t("streams.udpPublicationMonitor", "UDP publication monitor")}</strong>
        </div>
        <div className="toolbar-actions">
          <div
            className="segmented-control"
            aria-label={t("streams.filter", "Stream filter")}
          >
            <button
              className={filter === "all" ? "active" : ""}
              onClick={() => setFilter("all")}
              type="button"
            >
              {t("common.all", "All")}
            </button>
            <button
              className={filter === "active" ? "active" : ""}
              onClick={() => setFilter("active")}
              type="button"
            >
              {t("common.active", "Active")}
            </button>
          </div>
          <button
            className="secondary-button"
            onClick={refreshStreams}
            type="button"
          >
            <RefreshCw size={16} />
            {t("common.refresh", "Refresh")}
          </button>
        </div>
      </section>

      <section className="data-panel">
        <div className="panel-header">
          <h2>{t("streams.streamPreview", "Stream preview")}</h2>
          {selectedPreview ? (
            <StatusPill
              label={
                selectedPreview.kind === "synthetic"
                  ? t("common.mission", "Mission")
                  : t("common.snapshot", "Snapshot")
              }
              tone="neutral"
            />
          ) : null}
        </div>
        <StreamPreviewPanel
          isLoading={previewQuery.isFetching}
          preview={previewQuery.data}
          selectedPreview={selectedPreview}
          t={t}
        />
        {previewQuery.error ? (
          <div className="message error">{previewQuery.error.message}</div>
        ) : null}
      </section>

      <section className="data-panel">
        <div className="panel-header">
          <h2>{t("streams.syntheticUdpStreams", "Synthetic UDP streams")}</h2>
          <StatusPill
            label={`${syntheticStreams.length}/${syntheticQuery.data?.length ?? 0}`}
            tone="neutral"
          />
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("common.stream", "Stream")}</th>
                <th>{t("common.mission", "Mission")}</th>
                <th>{t("common.endpoint", "Endpoint")}</th>
                <th>{t("common.frequency", "Frequency")}</th>
                <th>{t("common.status", "Status")}</th>
                <th>{t("common.sent", "Sent")}</th>
                <th>{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody>
              {syntheticStreams.map((stream) => (
                <tr
                  className={
                    selectedPreview?.kind === "synthetic" &&
                    selectedPreview.streamId === stream.stream_id
                      ? "selected-row"
                      : undefined
                  }
                  key={stream.stream_id}
                >
                  <td className="code-cell">{stream.stream_id}</td>
                  <td className="code-cell">{stream.mission_id}</td>
                  <td>
                    {stream.host}:{stream.port}
                  </td>
                  <td>{stream.frequency_hz} Hz</td>
                  <td>
                    <StatusPill
                      label={
                        stream.is_active
                          ? t("common.active", "active")
                          : t("common.inactive", "inactive")
                      }
                      tone={stream.is_active ? "success" : "neutral"}
                    />
                  </td>
                  <td>{stream.sent_count}</td>
                  <td>
                    <button
                      className="secondary-button"
                      onClick={() =>
                        setSelectedPreview({
                          kind: "synthetic",
                          streamId: stream.stream_id,
                        })
                      }
                      type="button"
                    >
                      <Eye size={16} />
                      {t("streams.preview", "Preview")}
                    </button>
                    <button
                      className="danger-button"
                      disabled={
                        stopSyntheticMutation.isPending || !stream.is_active
                      }
                      onClick={() => stopSyntheticMutation.mutate(stream.stream_id)}
                      type="button"
                    >
                      <Square size={16} />
                      {t("common.stop", "Stop")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {syntheticStreams.length === 0 ? (
          <EmptyState
            label={
              filter === "active"
                ? t("streams.noActiveSyntheticStreams", "No active synthetic streams")
                : t("streams.noSyntheticStreams", "No synthetic streams")
            }
          />
        ) : null}
        {stopSyntheticMutation.error ? (
          <div className="message error">{stopSyntheticMutation.error.message}</div>
        ) : null}
      </section>

      <section className="data-panel">
        <div className="panel-header">
          <h2>{t("streams.snapshotUdpStreams", "Snapshot UDP streams")}</h2>
          <StatusPill
            label={`${snapshotStreams.length}/${snapshotQuery.data?.length ?? 0}`}
            tone="neutral"
          />
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("common.stream", "Stream")}</th>
                <th>{t("common.snapshot", "Snapshot")}</th>
                <th>{t("common.endpoint", "Endpoint")}</th>
                <th>{t("common.frequency", "Frequency")}</th>
                <th>{t("common.status", "Status")}</th>
                <th>{t("common.samples", "Samples")}</th>
                <th>{t("common.frames", "Frames")}</th>
                <th>{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody>
              {snapshotStreams.map((stream) => (
                <tr
                  className={
                    selectedPreview?.kind === "snapshot" &&
                    selectedPreview.streamId === stream.stream_id
                      ? "selected-row"
                      : undefined
                  }
                  key={stream.stream_id}
                >
                  <td className="code-cell">{stream.stream_id}</td>
                  <td className="code-cell">{stream.snapshot_id}</td>
                  <td>
                    {stream.host}:{stream.port}
                  </td>
                  <td>{stream.frequency_hz} Hz</td>
                  <td>
                    <StatusPill
                      label={
                        stream.is_active
                          ? t("common.active", "active")
                          : t("common.inactive", "inactive")
                      }
                      tone={stream.is_active ? "success" : "neutral"}
                    />
                  </td>
                  <td>{stream.samples_sent}</td>
                  <td>{stream.frames_sent}</td>
                  <td>
                    <button
                      className="secondary-button"
                      onClick={() =>
                        setSelectedPreview({
                          kind: "snapshot",
                          streamId: stream.stream_id,
                        })
                      }
                      type="button"
                    >
                      <Eye size={16} />
                      {t("streams.preview", "Preview")}
                    </button>
                    <button
                      className="danger-button"
                      disabled={stopSnapshotMutation.isPending || !stream.is_active}
                      onClick={() => stopSnapshotMutation.mutate(stream.stream_id)}
                      type="button"
                    >
                      <Square size={16} />
                      {t("common.stop", "Stop")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {snapshotStreams.length === 0 ? (
          <EmptyState
            label={
              filter === "active"
                ? t("streams.noActiveSnapshotStreams", "No active snapshot streams")
                : t("streams.noSnapshotStreams", "No snapshot streams")
            }
          />
        ) : null}
        {stopSnapshotMutation.error ? (
          <div className="message error">{stopSnapshotMutation.error.message}</div>
        ) : null}
      </section>
    </div>
  );
}

function StreamPreviewPanel({
  isLoading,
  preview,
  selectedPreview,
  t,
}: {
  isLoading: boolean;
  preview?: StreamPreviewResponse;
  selectedPreview: SelectedStreamPreview | null;
  t: Translate;
}) {
  if (selectedPreview === null) {
    return (
      <EmptyState
        label={t("streams.selectStreamForPreview", "Select a stream to preview")}
      />
    );
  }

  if (!preview || preview.samples.length === 0) {
    return (
      <EmptyState
        label={
          isLoading
            ? t("streams.previewLoading", "Loading stream preview")
            : t("streams.noPreviewSamples", "No stream messages captured yet")
        }
      />
    );
  }

  return (
    <div className="panel-body preview-stack">
      <div className="preview-heading">
        <strong>{t("streams.recentMessages", "Recent messages")}</strong>
        <StatusPill
          label={`${preview.samples.length} ${t("streams.captured", "captured")}`}
          tone="neutral"
        />
      </div>

      <div className="batch-preview">
        <table className="data-table compact-table">
          <thead>
            <tr>
              <th>{t("synthetic.messageNumber", "#")}</th>
              <th>{t("common.timestamp", "Timestamp")}</th>
              <th>{t("synthetic.droneId", "Drone ID")}</th>
              <th>{t("synthetic.altitudeM", "Altitude, m")}</th>
              <th>{t("synthetic.groundSpeed", "Ground speed, m/s")}</th>
              <th>{t("synthetic.batteryPercent", "Battery, %")}</th>
            </tr>
          </thead>
          <tbody>
            {preview.samples.map((sample, index) => (
              <tr key={`${sample.timestamp}-${index}`}>
                <td>{index + 1}</td>
                <td className="code-cell">{sample.timestamp}</td>
                <td>{sample.drone_id}</td>
                <td>{formatNumber(sample.altitude_m, 1)}</td>
                <td>{formatNumber(sample.ground_speed_m_s, 1)}</td>
                <td>{formatNumber(sample.battery_percent, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="json-details">
        <summary>{t("synthetic.showJson", "Show JSON")}</summary>
        <JsonPreview value={preview.samples} />
      </details>
    </div>
  );
}

function formatNumber(value: number | null | undefined, digits: number): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return value.toFixed(digits);
}
