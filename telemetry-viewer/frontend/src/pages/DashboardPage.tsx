import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import { AnalysisProfilePanel } from "../features/analysis-profile/components/AnalysisProfilePanel";
import { DetectorSelectorPanel } from "../features/analysis-profile/components/DetectorSelectorPanel";
import { SessionPanel } from "../features/analysis-sessions/components/SessionPanel";
import { AnalysisTimingPanel } from "../features/analysis-timing/components/AnalysisTimingPanel";
import { AnomalyResultsPanel } from "../features/anomaly-results/components/AnomalyResultsPanel";
import { DetectorOutputsPanel } from "../features/detector-comparison/components/DetectorOutputsPanel";
import { ManualTelemetryPanel } from "../features/telemetry-monitoring/components/ManualTelemetryPanel";
import { TelemetryOverview } from "../features/telemetry-monitoring/components/TelemetryOverview";
import {
  analyzeUnifiedTelemetry,
  createAnalysisSession,
  deleteAnalysisSession,
  getAnalysisProfile,
  getAnalysisSession,
  getAnalysisSessionState,
  listDetectors,
  updateAnalysisProfile,
  updateAnalysisSessionProfile,
} from "../shared/api/analysisServiceClient";
import { ApiError } from "../shared/api/http";
import type { AnomalyResult } from "../shared/contracts/anomalyResult";
import type { AnalysisProfile } from "../shared/contracts/analysisProfile";
import {
  parseTelemetryPayload,
  sampleTelemetryPayload,
  type TelemetryPayload,
} from "../shared/contracts/telemetry";
import { useI18n } from "../shared/i18n/I18nProvider";
import { EmptyState } from "../shared/ui/EmptyState";
import { formatDate, formatDurationMs } from "../shared/ui/format";
import { StatusPill } from "../shared/ui/StatusPill";
import {
  readActiveSessionId,
  writeActiveSessionId,
} from "../shared/state/activeSession";

type ResultHistoryEntry = {
  key: string;
  receivedAt: string;
  result: AnomalyResult;
  source: "manual" | "session";
  telemetry: TelemetryPayload | null;
};

export function DashboardPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionIdState] = useState(readActiveSessionId);
  const [profileDraft, setProfileDraft] = useState<AnalysisProfile | null>(null);
  const [profileDraftSourceKey, setProfileDraftSourceKey] = useState("");
  const [telemetryText, setTelemetryText] = useState(
    JSON.stringify(sampleTelemetryPayload, null, 2),
  );
  const [manualParseError, setManualParseError] = useState<string | null>(null);
  const [recentResults, setRecentResults] = useState<ResultHistoryEntry[]>([]);

  const detectorsQuery = useQuery({
    queryKey: ["analysis-detectors"],
    queryFn: listDetectors,
    refetchOnWindowFocus: false,
  });
  const profileQuery = useQuery({
    queryKey: ["analysis-profile"],
    queryFn: getAnalysisProfile,
    refetchOnWindowFocus: false,
  });
  const sessionStateQuery = useQuery({
    queryKey: ["analysis-session-state", activeSessionId],
    queryFn: () => getAnalysisSessionState(activeSessionId),
    enabled: activeSessionId.length > 0,
    refetchInterval: activeSessionId ? 1000 : false,
    retry: false,
  });
  useEffect(() => {
    const session = sessionStateQuery.data?.session;
    if (session) {
      const sourceKey = profileSourceKey("session", session.session_id, session.profile);
      if (profileDraftSourceKey !== sourceKey) {
        setProfileDraft(session.profile);
        setProfileDraftSourceKey(sourceKey);
      }
      return;
    }

    if (!activeSessionId && profileQuery.data) {
      const sourceKey = profileSourceKey("global", "default", profileQuery.data);
      if (profileDraftSourceKey !== sourceKey) {
        setProfileDraft(profileQuery.data);
        setProfileDraftSourceKey(sourceKey);
      }
    }
  }, [
    activeSessionId,
    profileDraftSourceKey,
    profileQuery.data,
    sessionStateQuery.data?.session,
  ]);

  const setActiveSessionId = useCallback((sessionId: string) => {
    const trimmed = sessionId.trim();
    writeActiveSessionId(trimmed);
    setActiveSessionIdState(trimmed);
  }, []);

  const rememberResult = useCallback(
    (
      source: ResultHistoryEntry["source"],
      result: AnomalyResult,
      telemetry: TelemetryPayload | null,
    ) => {
      const key = resultKey(result);
      setRecentResults((current) => {
        if (current.some((entry) => entry.key === key)) {
          return current;
        }
        return [
          {
            key,
            receivedAt: new Date().toISOString(),
            result,
            source,
            telemetry,
          },
          ...current,
        ].slice(0, 12);
      });
    },
    [],
  );

  useEffect(() => {
    if (sessionStateQuery.data?.last_result) {
      rememberResult(
        "session",
        sessionStateQuery.data.last_result,
        sessionStateQuery.data.last_telemetry,
      );
    }
  }, [sessionStateQuery.data, rememberResult]);

  const saveProfileMutation = useMutation({
    mutationFn: async (profile: AnalysisProfile) => {
      const savedProfile = await updateAnalysisProfile(profile);
      if (!activeSessionId) {
        return { profile: savedProfile, session: null };
      }
      let session = null;
      try {
        session = await updateAnalysisSessionProfile(activeSessionId, savedProfile);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) {
          throw error;
        }
        setActiveSessionId("");
      }
      return { profile: savedProfile, session };
    },
    onSuccess: ({ profile, session }) => {
      setProfileDraft(profile);
      queryClient.setQueryData(["analysis-profile"], profile);
      if (session) {
        queryClient.setQueryData(["analysis-session-state", session.session_id], {
          session,
          last_telemetry: null,
          last_result: null,
        });
      }
    },
  });
  const openSessionMutation = useMutation({
    mutationFn: async (request: {
      sessionId: string | null;
      droneId: string | null;
      profile: AnalysisProfile | null;
    }) => {
      const sessionId = request.sessionId?.trim() || null;
      if (sessionId) {
        try {
          return await getAnalysisSession(sessionId);
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 404) {
            throw error;
          }
        }
      }
      return createAnalysisSession({
        session_id: sessionId,
        drone_id: request.droneId,
        profile: request.profile,
      });
    },
    onSuccess: (session) => {
      setActiveSessionId(session.session_id);
      queryClient.setQueryData(["analysis-session-state", session.session_id], {
        session,
        last_telemetry: null,
        last_result: null,
      });
    },
  });
  const deleteSessionMutation = useMutation({
    mutationFn: deleteAnalysisSession,
    onSuccess: () => {
      setActiveSessionId("");
      void queryClient.invalidateQueries({ queryKey: ["analysis-listeners"] });
    },
  });
  const analyzeMutation = useMutation({
    mutationFn: (request: {
      sessionId: string;
      telemetry: TelemetryPayload;
    }) => analyzeUnifiedTelemetry(request.sessionId, request.telemetry),
    onSuccess: (result, request) => {
      rememberResult("manual", result, request.telemetry);
      void queryClient.invalidateQueries({
        queryKey: ["analysis-session-state", request.sessionId],
      });
    },
  });

  function analyzeManualTelemetry() {
    if (!activeSessionId) {
      setManualParseError(
        t("manual.sessionRequired", "Select or create an analysis session first."),
      );
      return;
    }

    try {
      const telemetry = parseTelemetryPayload(telemetryText);
      setManualParseError(null);
      analyzeMutation.mutate({ sessionId: activeSessionId, telemetry });
    } catch (error) {
      setManualParseError(error instanceof Error ? error.message : String(error));
    }
  }

  const currentResult =
    sessionStateQuery.data?.last_result ??
    analyzeMutation.data ??
    recentResults[0]?.result ??
    null;
  const currentTelemetry = currentResult
    ? sessionStateQuery.data?.last_telemetry ??
      recentResults.find(
        (entry) => entry.key === resultKey(currentResult) && entry.telemetry,
      )?.telemetry ?? null
    : null;

  return (
    <div className="dashboard-grid">
      <div className="dashboard-main">
        <SessionPanel
          activeSessionId={activeSessionId}
          createSessionError={asError(openSessionMutation.error)}
          deleteSessionError={asError(deleteSessionMutation.error)}
          isCreatingSession={openSessionMutation.isPending}
          isDeletingSession={deleteSessionMutation.isPending}
          onOpenSession={(sessionId, droneId) =>
            openSessionMutation.mutate({
              sessionId,
              droneId,
              profile: profileDraft,
            })
          }
          onDeleteSession={(sessionId) => deleteSessionMutation.mutate(sessionId)}
          onRefresh={() => {
            void sessionStateQuery.refetch();
          }}
          session={sessionStateQuery.data?.session}
          sessionLoadError={asError(sessionStateQuery.error)}
        />

        <DetectorSelectorPanel
          detectors={detectorsQuery.data?.detectors ?? []}
          error={firstError(saveProfileMutation.error, profileQuery.error)}
          isLoading={profileQuery.isLoading}
          isSaving={saveProfileMutation.isPending}
          onChange={setProfileDraft}
          onSave={() => {
            if (profileDraft) {
              saveProfileMutation.mutate(profileDraft);
            }
          }}
          profile={profileDraft}
        />

        <AnalysisTimingPanel
          detectors={detectorsQuery.data?.detectors ?? []}
          result={currentResult}
        />
        <TelemetryOverview result={currentResult} telemetry={currentTelemetry} />
        <AnomalyResultsPanel result={currentResult} />
        <DetectorOutputsPanel
          detectors={detectorsQuery.data?.detectors ?? []}
          result={currentResult}
        />
        <ResultHistoryPanel entries={recentResults} />
      </div>

      <aside className="dashboard-side">
        <AnalysisProfilePanel
          error={firstError(saveProfileMutation.error, profileQuery.error)}
          isLoading={profileQuery.isLoading}
          isSaving={saveProfileMutation.isPending}
          onChange={setProfileDraft}
          onSave={() => {
            if (profileDraft) {
              saveProfileMutation.mutate(profileDraft);
            }
          }}
          profile={profileDraft}
        />
        <ManualTelemetryPanel
          error={asError(analyzeMutation.error)}
          isAnalyzing={analyzeMutation.isPending}
          onAnalyze={analyzeManualTelemetry}
          onTelemetryTextChange={setTelemetryText}
          parseError={manualParseError}
          telemetryText={telemetryText}
        />
      </aside>
    </div>
  );
}

function ResultHistoryPanel({ entries }: { entries: ResultHistoryEntry[] }) {
  const { t } = useI18n();

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("history.title", "Recent results")}</h2>
        <StatusPill
          label={`${entries.length} ${t("history.cached", "cached")}`}
          tone="neutral"
        />
      </div>
      {entries.length > 0 ? (
        <div className="table-wrap">
          <table className="data-table compact-table">
            <thead>
              <tr>
                <th>{t("history.received", "Received")}</th>
                <th>{t("history.source", "Source")}</th>
                <th>{t("history.drone", "Drone")}</th>
                <th>{t("history.telemetryTimestamp", "Telemetry timestamp")}</th>
                <th>{t("history.analysisTime", "Analysis time")}</th>
                <th>{t("history.anomalies", "Anomalies")}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.key}>
                  <td>{formatDate(entry.receivedAt)}</td>
                  <td>{t(`source.${entry.source}`, entry.source)}</td>
                  <td className="code-cell">{entry.result.drone_id}</td>
                  <td className="code-cell">{entry.result.telemetry_timestamp}</td>
                  <td>{formatDurationMs(entry.result.timing?.total_ms)}</td>
                  <td>
                    <StatusPill
                      label={String(entry.result.anomalies.length)}
                      tone={entry.result.has_anomalies ? "danger" : "success"}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          label={t("history.empty", "No analysis results captured yet.")}
        />
      )}
    </section>
  );
}

function resultKey(result: AnomalyResult): string {
  return [
    result.drone_id,
    result.telemetry_timestamp,
    result.has_anomalies ? "1" : "0",
    result.anomalies.map((anomaly) => anomaly.type).join("."),
  ].join("|");
}

function profileSourceKey(
  scope: "global" | "session",
  id: string,
  profile: AnalysisProfile,
): string {
  return JSON.stringify({
    scope,
    id,
    enabled_detectors: profile.enabled_detectors,
    enabled_models: profile.enabled_models,
    history_size: profile.history_size,
    model_window_size: profile.model_window_size,
    thresholds: profile.thresholds,
  });
}

function firstError(...errors: unknown[]): Error | null {
  for (const error of errors) {
    const resolved = asError(error);
    if (resolved) {
      return resolved;
    }
  }
  return null;
}

function asError(error: unknown): Error | null {
  if (!error) {
    return null;
  }
  if (error instanceof Error) {
    return error;
  }
  return new Error(String(error));
}
