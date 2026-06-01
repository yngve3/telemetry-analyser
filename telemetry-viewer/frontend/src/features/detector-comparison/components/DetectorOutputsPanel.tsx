import type {
  AnomalyResult,
  DetectedAnomaly,
  Severity,
} from "../../../shared/contracts/anomalyResult";
import type { DetectorResponse } from "../../../shared/contracts/analysisProfile";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import {
  formatAnomalyType,
  formatDetectorName,
  formatMessage,
  isVisibleDetectorName,
  visibleDetectors,
} from "../../../shared/ui/display";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { formatDurationMs } from "../../../shared/ui/format";
import { JsonPreview } from "../../../shared/ui/JsonPreview";
import { StatusPill } from "../../../shared/ui/StatusPill";

type DetectorOutputsPanelProps = {
  detectors: DetectorResponse[];
  result: AnomalyResult | null;
};

const defaultDetectorNames = ["rule_based", "correlation_based", "autoencoder"];

export function DetectorOutputsPanel({
  detectors,
  result,
}: DetectorOutputsPanelProps) {
  const { t } = useI18n();
  const detectorNames =
    detectors.length > 0
      ? visibleDetectors(detectors).map((detector) => detector.name)
      : defaultDetectorNames;
  const reportedCount = Object.keys(result?.detector_outputs ?? {}).filter(
    isVisibleDetectorName,
  ).length;

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("detectors.title", "Detector outputs")}</h2>
        <StatusPill
          label={`${reportedCount} ${t("detectors.reported", "reported")}`}
          tone="neutral"
        />
      </div>

      {result ? (
        <div className="detector-output-grid">
          {detectorNames.map((name) => {
            const output = result.detector_outputs[name];
            return (
              <div className="detector-output" key={name}>
                <div className="detector-output-header">
                  <strong>{formatDetectorName(name, t)}</strong>
                  <div className="detector-output-meta">
                    <StatusPill
                      label={formatDurationMs(output?.duration_ms)}
                      tone={
                        typeof output?.duration_ms === "number"
                          ? "success"
                          : "neutral"
                      }
                    />
                    <StatusPill
                      label={
                        output?.status
                          ? t(`status.${output.status}`, output.status)
                          : t("detectors.notReported", "not reported")
                      }
                      tone={output?.status === "ready" ? "success" : "neutral"}
                    />
                  </div>
                </div>
                {output?.message ? (
                  <div className="message">{formatMessage(output.message, t)}</div>
                ) : null}
                {output?.anomalies?.length ? (
                  <div className="raw-anomaly-list">
                    {output.anomalies.map((anomaly, index) => (
                      <RawDetectorAnomaly
                        anomaly={anomaly}
                        key={`${anomaly.type}-${index}`}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    label={
                      output
                        ? t("detectors.noAnomalies", "No detector anomalies.")
                        : t("detectors.noOutputForDetector", "Detector did not report.")
                    }
                  />
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState label={t("detectors.noOutput", "No detector output yet.")} />
      )}
    </section>
  );
}

function RawDetectorAnomaly({ anomaly }: { anomaly: DetectedAnomaly }) {
  const { t } = useI18n();

  return (
    <div className="raw-anomaly">
      <div className="raw-anomaly-header">
        <strong className="code-title">{formatAnomalyType(anomaly.type, t)}</strong>
        <div className="raw-anomaly-meta">
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
      <div className="message">{formatMessage(anomaly.message, t)}</div>
      <details className="inline-details">
        <summary>{t("detectors.evidence", "Evidence")}</summary>
        <JsonPreview value={anomaly.evidence} />
      </details>
    </div>
  );
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
