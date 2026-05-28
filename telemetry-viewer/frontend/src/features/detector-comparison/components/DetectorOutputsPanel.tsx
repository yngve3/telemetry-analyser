import type {
  AnomalyResult,
  DetectedAnomaly,
  Severity,
} from "../../../shared/contracts/anomalyResult";
import type { DetectorResponse } from "../../../shared/contracts/analysisProfile";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { JsonPreview } from "../../../shared/ui/JsonPreview";
import { StatusPill } from "../../../shared/ui/StatusPill";

type DetectorOutputsPanelProps = {
  detectors: DetectorResponse[];
  result: AnomalyResult | null;
};

const defaultDetectorNames = ["rule_based", "ml", "nn_autoencoder"];

export function DetectorOutputsPanel({
  detectors,
  result,
}: DetectorOutputsPanelProps) {
  const { t } = useI18n();
  const detectorNames =
    detectors.length > 0
      ? detectors.map((detector) => detector.name)
      : defaultDetectorNames;

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("detectors.title", "Detector outputs")}</h2>
        <StatusPill
          label={`${Object.keys(result?.detector_outputs ?? {}).length} ${t("detectors.reported", "reported")}`}
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
                  <strong>{name}</strong>
                  <StatusPill
                    label={
                      output?.status
                        ? t(`status.${output.status}`, output.status)
                        : t("detectors.notReported", "not reported")
                    }
                    tone={output?.status === "ready" ? "success" : "neutral"}
                  />
                </div>
                {output?.message ? (
                  <div className="message">{output.message}</div>
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
        <strong className="code-title">{anomaly.type}</strong>
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
      <div className="message">{anomaly.message}</div>
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
