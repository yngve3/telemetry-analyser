import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { Play, Plus, Square, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import {
  createExternalSource,
  deleteExternalSource,
  getExternalSourceStatus,
  listExternalSources,
  startExternalSource,
  stopExternalSource,
} from "../features/external/api";
import type { ExternalSourceCreateRequest } from "../shared/api/types";
import { useI18n } from "../shared/i18n/I18nProvider";
import { EmptyState } from "../shared/ui/EmptyState";
import { JsonPreview } from "../shared/ui/JsonPreview";
import { StatusPill } from "../shared/ui/StatusPill";
import { validatePort } from "../shared/validation/forms";

const initialForm: ExternalSourceCreateRequest = {
  name: "external_mavlink",
  address: "0.0.0.0",
  port: 14540,
  protocol: "udp",
  forward_enabled: true,
  forward_host: "analysis-service",
  forward_port: 14560,
};

export function ExternalPage() {
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const [form, setForm] = useState<ExternalSourceCreateRequest>(initialForm);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: ["external-sources"],
    queryFn: listExternalSources,
    refetchInterval: 2500,
  });
  const selectedSourceQuery = useQuery({
    queryKey: ["external-source", selectedSourceId],
    queryFn: () => getExternalSourceStatus(selectedSourceId as string),
    enabled: selectedSourceId !== null,
    refetchInterval: 1500,
  });

  const createMutation = useMutation({
    mutationFn: createExternalSource,
    onSuccess: (response) => {
      setSelectedSourceId(response.source_id);
      return queryClient.invalidateQueries({ queryKey: ["external-sources"] });
    },
  });
  const startMutation = useMutation({
    mutationFn: startExternalSource,
    onSuccess: (response) => {
      setSelectedSourceId(response.source_id);
      return invalidateExternalQueries(queryClient, response.source_id);
    },
  });
  const stopMutation = useMutation({
    mutationFn: stopExternalSource,
    onSuccess: (response) => invalidateExternalQueries(queryClient, response.source_id),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteExternalSource,
    onSuccess: (response) => {
      if (selectedSourceId === response.source_id) {
        setSelectedSourceId(null);
      }
      void queryClient.invalidateQueries({ queryKey: ["external-sources"] });
      void queryClient.removeQueries({
        queryKey: ["external-source", response.source_id],
      });
    },
  });

  useEffect(() => {
    if (selectedSourceId === null && sourcesQuery.data?.length) {
      setSelectedSourceId(sourcesQuery.data[0].source_id);
    }
  }, [selectedSourceId, sourcesQuery.data]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (form.name.trim().length === 0) {
      setFormError(t("validation.sourceNameRequired", "Source name is required."));
      return;
    }
    if (form.address.trim().length === 0) {
      setFormError(t("validation.addressRequired", "Address is required."));
      return;
    }

    const portError = validatePort(
      form.port,
      t("validation.portRange", "Port must be an integer within [1, 65535]."),
    );
    if (portError !== null) {
      setFormError(portError);
      return;
    }

    setFormError(null);
    createMutation.mutate(form);
  }

  return (
    <div className="page-grid">
      <section className="tool-panel">
        <div className="panel-header">
          <h2>{t("external.registerSource", "Register source")}</h2>
        </div>

        <form onSubmit={submit}>
          <div className="form-grid">
            <label className="field">
              <span>{t("common.name", "Name")}</span>
              <input
                required
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <label className="field">
              <span>{t("common.protocol", "Protocol")}</span>
              <select
                value={form.protocol}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    protocol: event.target.value as "udp",
                  }))
                }
              >
                <option value="udp">udp</option>
              </select>
            </label>
            <label className="field">
              <span>{t("common.address", "Address")}</span>
              <input
                required
                value={form.address}
                onChange={(event) =>
                  setForm((current) => ({ ...current, address: event.target.value }))
                }
              />
            </label>
            <label className="field">
              <span>{t("common.port", "Port")}</span>
              <input
                max="65535"
                min="1"
                required
                type="number"
                value={form.port}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    port: Number(event.target.value),
                  }))
                }
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={createMutation.isPending}
              type="submit"
            >
              <Plus size={17} />
              {t("external.registerSource", "Register source")}
            </button>
          </div>

          {createMutation.error ? (
            <div className="message error">{createMutation.error.message}</div>
          ) : null}
          {formError ? <div className="message error">{formError}</div> : null}
        </form>
      </section>

      <div className="page-stack">
        <section className="data-panel">
          <div className="panel-header">
            <h2>{t("external.sources", "Sources")}</h2>
            <StatusPill
              label={`${sourcesQuery.data?.length ?? 0} ${t("external.registered", "registered")}`}
              tone="neutral"
            />
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("common.name", "Name")}</th>
                  <th>{t("common.endpoint", "Endpoint")}</th>
                  <th>{t("common.status", "Status")}</th>
                  <th>{t("external.packets", "Packets")}</th>
                  <th>{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody>
                {sourcesQuery.data?.map((source) => (
                  <tr key={source.source_id}>
                    <td>
                      <button
                        className="ghost-button"
                        onClick={() => setSelectedSourceId(source.source_id)}
                        type="button"
                      >
                        {source.name}
                      </button>
                    </td>
                    <td>
                      {source.address}:{source.port}/{source.protocol}
                    </td>
                    <td>
                      <StatusPill
                        label={
                          source.is_active
                            ? t("common.active", "active")
                            : t("common.inactive", "inactive")
                        }
                        tone={source.is_active ? "success" : "neutral"}
                      />
                    </td>
                    <td>{source.received_packets}</td>
                    <td>
                      <div className="source-action-row">
                        <button
                          aria-label={
                            source.is_active
                              ? t("common.stop", "Stop")
                              : t("common.start", "Start")
                          }
                          className="icon-button"
                          disabled={startMutation.isPending || stopMutation.isPending}
                          onClick={() =>
                            source.is_active
                              ? stopMutation.mutate(source.source_id)
                              : startMutation.mutate(source.source_id)
                          }
                          title={
                            source.is_active
                              ? t("common.stop", "Stop")
                              : t("common.start", "Start")
                          }
                          type="button"
                        >
                          {source.is_active ? <Square size={16} /> : <Play size={16} />}
                        </button>
                        <button
                          aria-label={t("common.delete", "Delete")}
                          className="icon-button danger-icon-button"
                          disabled={deleteMutation.isPending}
                          onClick={() => deleteMutation.mutate(source.source_id)}
                          title={t("common.delete", "Delete")}
                          type="button"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {sourcesQuery.data?.length === 0 ? (
            <EmptyState label={t("external.noSources", "No sources")} />
          ) : null}
        </section>

        <section className="data-panel">
          <div className="panel-header">
            <h2>{t("common.status", "Status")}</h2>
            {selectedSourceQuery.data ? (
              <StatusPill
                label={
                  selectedSourceQuery.data.is_active
                    ? t("common.active", "active")
                    : t("common.inactive", "inactive")
                }
                tone={selectedSourceQuery.data.is_active ? "success" : "neutral"}
              />
            ) : null}
          </div>

          {selectedSourceQuery.data ? (
            <div className="panel-body">
              <div className="metric-grid">
                <Metric
                  label={t("external.receivedPackets", "Received packets")}
                  value={selectedSourceQuery.data.received_packets}
                />
                <Metric
                  label={t("external.receivedBytes", "Received bytes")}
                  value={selectedSourceQuery.data.received_bytes}
                />
                <Metric
                  label={t("external.forwardedPackets", "Forwarded packets")}
                  value={selectedSourceQuery.data.forwarded_packets}
                />
                <Metric
                  label={t("external.forwardTarget", "Forward target")}
                  value={
                    selectedSourceQuery.data.forward_enabled
                      ? `${selectedSourceQuery.data.forward_host}:${selectedSourceQuery.data.forward_port}`
                      : "-"
                  }
                />
                <Metric
                  label={t("external.lastPayload", "Last payload")}
                  value={selectedSourceQuery.data.last_payload_size ?? "-"}
                />
                <Metric
                  label={t("external.remote", "Remote")}
                  value={
                    selectedSourceQuery.data.last_remote_address
                      ? `${selectedSourceQuery.data.last_remote_address}:${selectedSourceQuery.data.last_remote_port}`
                      : "-"
                  }
                />
              </div>
              <PayloadPreview source={selectedSourceQuery.data} />
              {selectedSourceQuery.data.last_error ? (
                <div className="message error">
                  {t("external.lastError", "Last error")}:{" "}
                  {selectedSourceQuery.data.last_error}
                </div>
              ) : null}
              {selectedSourceQuery.data.last_forward_error ? (
                <div className="message error">
                  {t("external.lastForwardError", "Last forward error")}:{" "}
                  {selectedSourceQuery.data.last_forward_error}
                </div>
              ) : null}
            </div>
          ) : (
            <EmptyState label={t("external.noSourceSelected", "No source selected")} />
          )}

          {startMutation.error ? (
            <div className="message error">{startMutation.error.message}</div>
          ) : null}
          {stopMutation.error ? (
            <div className="message error">{stopMutation.error.message}</div>
          ) : null}
          {deleteMutation.error ? (
            <div className="message error">{deleteMutation.error.message}</div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function PayloadPreview({
  source,
}: {
  source: {
    last_payload_preview_ascii?: string | null;
    last_payload_preview_hex?: string | null;
    last_payload_preview_truncated?: boolean;
  };
}) {
  const { t } = useI18n();
  if (!source.last_payload_preview_hex) {
    return (
      <div className="message">
        {t("external.payloadPreviewEmpty", "No payload received yet")}
      </div>
    );
  }
  return (
    <div className="preview-stack">
      <div className="preview-heading">
        <strong>{t("external.payloadPreview", "Payload preview")}</strong>
        {source.last_payload_preview_truncated ? (
          <StatusPill label="truncated" tone="warning" />
        ) : null}
      </div>
      <JsonPreview
        value={{
          hex: source.last_payload_preview_hex,
          ascii: source.last_payload_preview_ascii,
        }}
      />
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

function invalidateExternalQueries(queryClient: QueryClient, id: string) {
  void queryClient.invalidateQueries({ queryKey: ["external-sources"] });
  void queryClient.invalidateQueries({ queryKey: ["external-source", id] });
}
