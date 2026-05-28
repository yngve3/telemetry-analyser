import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plug, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import {
  createListener,
  deleteListener,
  getListener,
  listListeners,
} from "../shared/api/analysisServiceClient";
import type { ListenerResponse } from "../shared/contracts/analysisProfile";
import { useI18n } from "../shared/i18n/I18nProvider";
import { EmptyState } from "../shared/ui/EmptyState";
import { formatDate, formatText } from "../shared/ui/format";
import { JsonPreview } from "../shared/ui/JsonPreview";
import { Metric } from "../shared/ui/Metric";
import { StatusPill } from "../shared/ui/StatusPill";

export function ListenersPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [selectedListenerId, setSelectedListenerId] = useState("");
  const [sessionId, setSessionId] = useState("uav-001");
  const [bindHost, setBindHost] = useState("0.0.0.0");
  const [bindPort, setBindPort] = useState(14560);
  const [bufferSize, setBufferSize] = useState(4096);

  const listenersQuery = useQuery({
    queryKey: ["analysis-listeners"],
    queryFn: listListeners,
    refetchInterval: 1500,
  });
  const listenerQuery = useQuery({
    queryKey: ["analysis-listener", selectedListenerId],
    queryFn: () => getListener(selectedListenerId),
    enabled: selectedListenerId.length > 0,
    refetchInterval: selectedListenerId ? 1000 : false,
    retry: false,
  });

  useEffect(() => {
    if (selectedListenerId) {
      return;
    }
    const firstListener = listenersQuery.data?.[0];
    if (firstListener) {
      setSelectedListenerId(firstListener.listener_id);
    }
  }, [listenersQuery.data, selectedListenerId]);

  const createMutation = useMutation({
    mutationFn: createListener,
    onSuccess: (listener) => {
      setSelectedListenerId(listener.listener_id);
      void queryClient.invalidateQueries({ queryKey: ["analysis-listeners"] });
      void queryClient.invalidateQueries({
        queryKey: ["analysis-session-state", listener.session_id],
      });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteListener,
    onSuccess: (response) => {
      if (response.listener_id === selectedListenerId) {
        setSelectedListenerId("");
      }
      void queryClient.invalidateQueries({ queryKey: ["analysis-listeners"] });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createMutation.mutate({
      session_id: sessionId.trim(),
      protocol: "udp",
      format: "mavlink.v2",
      bind_host: bindHost.trim(),
      bind_port: bindPort,
      buffer_size: bufferSize,
    });
  }

  function refresh() {
    void listenersQuery.refetch();
    void listenerQuery.refetch();
  }

  const listeners = listenersQuery.data ?? [];
  const selectedListener =
    listenerQuery.data ??
    listeners.find((listener) => listener.listener_id === selectedListenerId);

  return (
    <div className="listener-page-grid">
      <section className="data-panel">
        <div className="panel-header">
          <h2>{t("listeners.createTitle", "Create listener")}</h2>
          <button className="icon-button" onClick={refresh} type="button">
            <RefreshCw size={17} />
          </button>
        </div>

        <form className="panel-body" onSubmit={submit}>
          <div className="form-grid">
            <label className="field">
              <span>{t("listeners.sessionId", "Session ID")}</span>
              <input
                required
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
              />
            </label>
            <label className="field">
              <span>{t("listeners.bindHost", "Bind host")}</span>
              <input
                required
                value={bindHost}
                onChange={(event) => setBindHost(event.target.value)}
              />
            </label>
            <label className="field">
              <span>{t("listeners.bindPort", "Bind port")}</span>
              <input
                max="65535"
                min="1"
                required
                type="number"
                value={bindPort}
                onChange={(event) => setBindPort(Number(event.target.value))}
              />
            </label>
            <label className="field">
              <span>{t("listeners.bufferSize", "Buffer size")}</span>
              <input
                min="1"
                required
                type="number"
                value={bufferSize}
                onChange={(event) => setBufferSize(Number(event.target.value))}
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={createMutation.isPending || sessionId.trim().length === 0}
              type="submit"
            >
              <Plug size={16} />
              {t("listeners.create", "Create listener")}
            </button>
            <button
              className="danger-button"
              disabled={!selectedListenerId || deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(selectedListenerId)}
              type="button"
            >
              <Trash2 size={16} />
              {t("listeners.deleteSelected", "Delete selected")}
            </button>
          </div>

          {createMutation.error ? (
            <div className="message error">
              {asError(createMutation.error).message}
            </div>
          ) : null}
          {deleteMutation.error ? (
            <div className="message error">
              {asError(deleteMutation.error).message}
            </div>
          ) : null}
        </form>
      </section>

      <section className="data-panel">
        <div className="panel-header">
          <h2>{t("listeners.stateTitle", "Listener state")}</h2>
          <StatusPill
            label={
              selectedListener?.status
                ? t(`status.${selectedListener.status}`, selectedListener.status)
                : t("listeners.notSelected", "not selected")
            }
            tone={selectedListener?.status === "active" ? "success" : "neutral"}
          />
        </div>
        {selectedListener ? (
          <ListenerDetails listener={selectedListener} />
        ) : (
          <EmptyState
            label={t(
              "listeners.inspectEmpty",
              "Select a listener to inspect transport metrics.",
            )}
          />
        )}
        {listenerQuery.error ? (
          <div className="message error panel-message">
            {asError(listenerQuery.error).message}
          </div>
        ) : null}
      </section>

      <section className="data-panel listener-table-panel">
        <div className="panel-header">
          <h2>{t("listeners.tableTitle", "Listeners")}</h2>
          <StatusPill
            label={`${listeners.length} ${t("listeners.total", "total")}`}
            tone="neutral"
          />
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("listeners.id", "ID")}</th>
                <th>{t("listeners.session", "Session")}</th>
                <th>{t("listeners.endpoint", "Endpoint")}</th>
                <th>{t("listeners.status", "Status")}</th>
                <th>{t("listeners.packets", "Packets")}</th>
                <th>{t("listeners.converted", "Converted")}</th>
                <th>{t("listeners.errors", "Errors")}</th>
                <th>{t("listeners.lastReceived", "Last received")}</th>
                <th>{t("listeners.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody>
              {listeners.map((listener) => (
                <tr
                  className={
                    listener.listener_id === selectedListenerId
                      ? "selected-row"
                      : undefined
                  }
                  key={listener.listener_id}
                >
                  <td className="code-cell">
                    <button
                      className="ghost-button"
                      onClick={() => setSelectedListenerId(listener.listener_id)}
                      type="button"
                    >
                      {listener.listener_id}
                    </button>
                  </td>
                  <td className="code-cell">{listener.session_id}</td>
                  <td>
                    {listener.bind_host}:{listener.bind_port}
                  </td>
                  <td>
                    <StatusPill
                      label={t(`status.${listener.status}`, listener.status)}
                      tone={listener.status === "active" ? "success" : "neutral"}
                    />
                  </td>
                  <td>{listener.received_packets}</td>
                  <td>{listener.converted_samples}</td>
                  <td>{listener.analysis_errors}</td>
                  <td>{formatDate(listener.last_received_at)}</td>
                  <td>
                    <button
                      className="danger-button"
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(listener.listener_id)}
                      type="button"
                    >
                      <Trash2 size={16} />
                      {t("listeners.delete", "Delete")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {listeners.length === 0 ? (
          <EmptyState label={t("listeners.empty", "No analysis listeners.")} />
        ) : null}
      </section>
    </div>
  );
}

function ListenerDetails({ listener }: { listener: ListenerResponse }) {
  const { t } = useI18n();

  return (
    <div className="panel-body">
      <div className="metric-grid listener-metrics">
        <Metric label={t("listeners.listenerId", "Listener ID")} value={listener.listener_id} />
        <Metric label={t("listeners.sessionId", "Session ID")} value={listener.session_id} />
        <Metric
          label={t("listeners.endpoint", "Endpoint")}
          value={`${listener.bind_host}:${listener.bind_port}`}
        />
        <Metric label={t("listeners.protocol", "Protocol")} value={listener.protocol} />
        <Metric label={t("listeners.format", "Format")} value={listener.format} />
        <Metric label={t("listeners.packets", "Packets")} value={String(listener.received_packets)} />
        <Metric label={t("listeners.bytes", "Bytes")} value={String(listener.received_bytes)} />
        <Metric label={t("listeners.converted", "Converted")} value={String(listener.converted_samples)} />
        <Metric label={t("listeners.errors", "Errors")} value={String(listener.analysis_errors)} />
        <Metric
          label={t("listeners.remoteAddress", "Remote address")}
          value={formatText(listener.last_remote_address)}
        />
        <Metric
          label={t("listeners.remotePort", "Remote port")}
          value={formatText(listener.last_remote_port)}
        />
        <Metric
          label={t("listeners.telemetryTimestamp", "Telemetry timestamp")}
          value={formatText(listener.last_telemetry_timestamp)}
        />
      </div>

      {listener.last_error ? (
        <div className="message error">{listener.last_error}</div>
      ) : null}

      <details className="json-details">
        <summary>{t("listeners.lastResult", "Last result")}</summary>
        {listener.last_result ? (
          <JsonPreview value={listener.last_result} />
        ) : (
          <EmptyState
            label={t(
              "listeners.noResult",
              "No result captured by this listener yet.",
            )}
          />
        )}
      </details>
    </div>
  );
}

function asError(error: unknown): Error {
  if (error instanceof Error) {
    return error;
  }
  return new Error(String(error));
}
