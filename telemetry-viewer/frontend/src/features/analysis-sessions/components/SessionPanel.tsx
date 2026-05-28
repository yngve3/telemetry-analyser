import { RefreshCw, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { AnalysisSession } from "../../../shared/contracts/analysisProfile";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import { formatDate, formatText } from "../../../shared/ui/format";

type SessionPanelProps = {
  activeSessionId: string;
  createSessionError: Error | null;
  deleteSessionError: Error | null;
  isCreatingSession: boolean;
  isDeletingSession: boolean;
  onCreateSession: (sessionId: string | null, droneId: string | null) => void;
  onDeleteSession: (sessionId: string) => void;
  onRefresh: () => void;
  onSetActiveSessionId: (sessionId: string) => void;
  session: AnalysisSession | undefined;
  sessionLoadError: Error | null;
};

export function SessionPanel({
  activeSessionId,
  createSessionError,
  deleteSessionError,
  isCreatingSession,
  isDeletingSession,
  onCreateSession,
  onDeleteSession,
  onRefresh,
  onSetActiveSessionId,
  session,
  sessionLoadError,
}: SessionPanelProps) {
  const { t } = useI18n();
  const [sessionIdInput, setSessionIdInput] = useState("uav-001");
  const [droneIdInput, setDroneIdInput] = useState("uav-001");

  function submitSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onCreateSession(emptyToNull(sessionIdInput), emptyToNull(droneIdInput));
  }

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("session.title", "Session panel")}</h2>
        <button className="icon-button" onClick={onRefresh} type="button">
          <RefreshCw size={17} />
        </button>
      </div>

      <div className="panel-body">
        <form className="sub-panel" onSubmit={submitSession}>
          <div className="sub-panel-title">
            {t("session.analysisSession", "Analysis session")}
          </div>
          <div className="form-grid">
            <label className="field">
              <span>{t("session.id", "Session ID")}</span>
              <input
                value={sessionIdInput}
                onChange={(event) => setSessionIdInput(event.target.value)}
              />
            </label>
            <label className="field">
              <span>{t("session.droneId", "Drone ID")}</span>
              <input
                value={droneIdInput}
                onChange={(event) => setDroneIdInput(event.target.value)}
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={isCreatingSession}
              type="submit"
            >
              {t("session.create", "Create session")}
            </button>
            <button
              className="secondary-button"
              onClick={() => onSetActiveSessionId(sessionIdInput.trim())}
              type="button"
            >
              {t("session.select", "Select")}
            </button>
            <button
              className="danger-button"
              disabled={!activeSessionId || isDeletingSession}
              onClick={() => onDeleteSession(activeSessionId)}
              type="button"
            >
              <Trash2 size={16} />
              {t("session.delete", "Delete")}
            </button>
          </div>

          <div className="metric-grid session-metrics">
            <SessionMetric
              label={t("session.activeId", "Active ID")}
              value={formatText(activeSessionId)}
            />
            <SessionMetric
              label={t("session.droneId", "Drone ID")}
              value={formatText(session?.drone_id)}
            />
            <SessionMetric
              label={t("session.samples", "Samples")}
              value={formatText(session?.samples_analyzed)}
            />
            <SessionMetric
              label={t("session.lastAnalyzed", "Last analyzed")}
              value={formatDate(session?.last_analyzed_at)}
            />
          </div>

          {sessionLoadError ? (
            <div className="message error">{sessionLoadError.message}</div>
          ) : null}
          {createSessionError ? (
            <div className="message error">{createSessionError.message}</div>
          ) : null}
          {deleteSessionError ? (
            <div className="message error">{deleteSessionError.message}</div>
          ) : null}
        </form>
      </div>
    </section>
  );
}

function SessionMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric compact-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}
