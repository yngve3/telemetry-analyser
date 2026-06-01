import type {
  AggregatedAnomaly,
  AnomalyResult,
  AnomalySource,
  Severity,
} from "../../../shared/contracts/anomalyResult";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import {
  formatAnomalyType,
  formatCause,
  formatDetectorName,
  formatMessage,
  isVisibleDetectorName,
} from "../../../shared/ui/display";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { JsonPreview } from "../../../shared/ui/JsonPreview";
import { StatusPill } from "../../../shared/ui/StatusPill";

type AnomalyResultsPanelProps = {
  result: AnomalyResult | null;
};

export function AnomalyResultsPanel({ result }: AnomalyResultsPanelProps) {
  const { t } = useI18n();
  const anomalies = result?.anomalies ?? [];

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("anomalies.title", "Anomaly results")}</h2>
        <StatusPill
          label={
            result === null
              ? t("anomalies.noResult", "no result")
              : result.has_anomalies
                ? `${anomalies.length} ${t("anomalies.found", "found")}`
                : t("anomalies.clear", "clear")
          }
          tone={
            result === null ? "neutral" : result.has_anomalies ? "danger" : "success"
          }
        />
      </div>

      {result && anomalies.length > 0 ? (
        <div className="anomaly-card-list">
          {anomalies.map((anomaly, index) => (
            <AnomalyCard
              anomaly={anomaly}
              key={`${anomaly.type}-${index}`}
              result={result}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          label={
            result
              ? t("anomalies.noneLatest", "No anomalies in the latest result.")
              : t("anomalies.none", "No analysis result yet.")
          }
        />
      )}
    </section>
  );
}

function AnomalyCard({
  anomaly,
  result,
}: {
  anomaly: AggregatedAnomaly;
  result: AnomalyResult;
}) {
  const { t } = useI18n();
  const visibleSources = anomaly.sources.filter((source) =>
    isVisibleDetectorName(source.detector),
  );
  const detectorNames = Array.from(
    new Set([
      ...visibleSources.map((source) => source.detector),
      ...Object.keys(result.detector_outputs),
    ]),
  ).filter(isVisibleDetectorName);

  return (
    <article className="anomaly-card">
      <div className="anomaly-card-header">
        <div>
          <strong className="code-title">{formatAnomalyType(anomaly.type, t)}</strong>
          <p>{formatMessage(anomaly.message, t)}</p>
        </div>
        <div className="anomaly-card-meta">
          <StatusPill
            label={t(`severity.${anomaly.severity}`, anomaly.severity)}
            tone={severityTone(anomaly.severity)}
          />
          <StatusPill
            label={`${Math.round(anomaly.confidence * 100)}%`}
            tone="neutral"
          />
        </div>
      </div>

      <div className="source-chip-row" aria-label={t("anomalies.sources", "Sources")}>
        {visibleSources.length > 0 ? (
          visibleSources.map((source) => (
            <span className="source-chip confirmed" key={source.detector}>
              <strong>{formatDetectorName(source.detector, t)}</strong>
              <span>{formatConfidence(source.confidence)}</span>
            </span>
          ))
        ) : (
          <span className="source-chip">
            {t("anomalies.noSources", "No detector sources")}
          </span>
        )}
      </div>

      {anomaly.probable_cause ||
      (anomaly.cause_confidence !== undefined &&
        anomaly.cause_confidence !== null) ? (
        <div className="source-chip-row">
          {anomaly.probable_cause ? (
            <span className="source-chip">
              <strong>{t("anomalies.cause", "Cause")}</strong>
              <span>{formatCause(anomaly.probable_cause, t)}</span>
            </span>
          ) : null}
          {anomaly.cause_confidence !== undefined &&
          anomaly.cause_confidence !== null ? (
            <span className="source-chip">
              <strong>{t("anomalies.causeConfidence", "Cause confidence")}</strong>
              <span>{formatConfidence(anomaly.cause_confidence)}</span>
            </span>
          ) : null}
        </div>
      ) : null}
      {anomaly.recommended_action ? (
        <div className="message">
          {t("anomalies.action", "Action")}:{" "}
          {formatMessage(anomaly.recommended_action, t)}
        </div>
      ) : null}

      <details className="contribution-details">
        <summary>{t("anomalies.contributions", "Detector contribution")}</summary>
        <div className="contribution-grid">
          {anomaly.sources.map((source) => (
            isVisibleDetectorName(source.detector) ? (
              <SourceContribution source={source} key={source.detector} />
            ) : null
          ))}
        </div>
      </details>

      <details className="contribution-details">
        <summary>{t("anomalies.detectorSignals", "Other detector signals")}</summary>
        <div className="detector-signal-grid">
          {detectorNames.map((detectorName) => {
            const source = anomaly.sources.find(
              (item) => item.detector === detectorName,
            );
            const output = result.detector_outputs[detectorName];
            const rawAnomalies = output?.anomalies ?? [];
            const sameTypeAnomalies =
              rawAnomalies.filter((item) => item.type === anomaly.type);
            const otherAnomalyCount =
              rawAnomalies.filter((item) => item.type !== anomaly.type).length;
            return (
              <div className="detector-signal" key={detectorName}>
                <div className="detector-signal-header">
                  <strong>{formatDetectorName(detectorName, t)}</strong>
                  <StatusPill
                    label={detectorSignalLabel({
                      hasSource: Boolean(source),
                      otherAnomalyCount,
                      sameTypeCount: sameTypeAnomalies.length,
                      t,
                    })}
                    tone={
                      source || sameTypeAnomalies.length > 0
                        ? "success"
                        : otherAnomalyCount > 0
                          ? "warning"
                          : "neutral"
                    }
                  />
                </div>
                {source ? (
                  <div className="message">
                    {t("anomalies.aggregatedSource", "Used by aggregator")}:{" "}
                    {formatConfidence(source.confidence)}
                  </div>
                ) : null}
                {rawAnomalies.length > 0 ? (
                  <JsonPreview value={rawAnomalies} />
                ) : null}
              </div>
            );
          })}
        </div>
      </details>
    </article>
  );
}

function SourceContribution({ source }: { source: AnomalySource }) {
  const { t } = useI18n();

  return (
    <div className="source-contribution">
      <div className="source-contribution-header">
        <strong>{formatDetectorName(source.detector, t)}</strong>
        <StatusPill label={formatConfidence(source.confidence)} tone="neutral" />
      </div>
      {source.severity ? (
        <StatusPill
          label={t(`severity.${source.severity}`, source.severity)}
          tone={severityTone(source.severity)}
        />
      ) : null}
      {source.message ? (
        <div className="message">{formatMessage(source.message, t)}</div>
      ) : null}
      <JsonPreview value={source.evidence} />
    </div>
  );
}

function detectorSignalLabel({
  hasSource,
  otherAnomalyCount,
  sameTypeCount,
  t,
}: {
  hasSource: boolean;
  otherAnomalyCount: number;
  sameTypeCount: number;
  t: (key: string, fallback?: string) => string;
}): string {
  if (hasSource) {
    return t("anomalies.confirmed", "confirmed");
  }
  if (sameTypeCount > 0) {
    return t("anomalies.rawSameType", "raw same type");
  }
  if (otherAnomalyCount > 0) {
    return `${otherAnomalyCount} ${t("anomalies.otherRaw", "other")}`;
  }
  return t("anomalies.noRawSignal", "no raw signal");
}

function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function severityTone(severity: Severity) {
  if (severity === "CRITICAL") {
    return "danger";
  }
  if (severity === "WARNING") {
    return "warning";
  }
  return "neutral";
}
