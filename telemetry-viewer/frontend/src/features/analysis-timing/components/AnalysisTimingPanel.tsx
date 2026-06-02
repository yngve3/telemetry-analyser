import type { DetectorResponse } from "../../../shared/contracts/analysisProfile";
import type {
  AnomalyResult,
  DetectorTiming,
} from "../../../shared/contracts/anomalyResult";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import {
  formatDetectorName,
  isVisibleDetectorName,
  supportedAnalyzerNames,
  visibleDetectors,
} from "../../../shared/ui/display";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { formatDurationMs } from "../../../shared/ui/format";
import { StatusPill } from "../../../shared/ui/StatusPill";

type AnalysisTimingPanelProps = {
  detectors: DetectorResponse[];
  result: AnomalyResult | null;
};

const defaultDetectorNames = [...supportedAnalyzerNames];

export function AnalysisTimingPanel({
  detectors,
  result,
}: AnalysisTimingPanelProps) {
  const { t } = useI18n();
  const timingByDetector = buildDetectorTiming(result);
  const detectorNames = buildDetectorNames(detectors, result, timingByDetector);
  const durations = detectorNames
    .map((name) => detectorDurationMs(result, timingByDetector, name))
    .filter(isFiniteNumber);
  const maxDurationMs = Math.max(...durations, 1);
  const totalMs = result?.timing?.total_ms;

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("timing.title", "Analysis timing")}</h2>
        <StatusPill
          label={formatDurationMs(totalMs)}
          tone={isFiniteNumber(totalMs) ? "success" : "neutral"}
        />
      </div>

      {result ? (
        <div className="timing-layout">
          <div className="timing-total-card">
            <span>{t("timing.total", "Total time")}</span>
            <strong>{formatDurationMs(totalMs)}</strong>
          </div>

          <div className="timing-detector-list">
            {detectorNames.map((name) => {
              const output = result.detector_outputs[name];
              const timing = timingByDetector[name];
              const durationMs = detectorDurationMs(result, timingByDetector, name);
              const width = isFiniteNumber(durationMs)
                ? Math.max((durationMs / maxDurationMs) * 100, 4)
                : 0;

              return (
                <div className="timing-detector-row" key={name}>
                  <div className="timing-detector-header">
                    <strong>{formatDetectorName(name, t)}</strong>
                    <div className="timing-detector-meta">
                      <StatusPill
                        label={formatDurationMs(durationMs)}
                        tone={isFiniteNumber(durationMs) ? "success" : "neutral"}
                      />
                      <StatusPill
                        label={detectorStatusLabel(timing?.status ?? output?.status, t)}
                        tone={statusTone(timing?.status ?? output?.status)}
                      />
                    </div>
                  </div>
                  <div
                    aria-label={`${formatDetectorName(name, t)} ${t("timing.duration", "Duration")}`}
                    className="timing-track"
                  >
                    <span style={{ width: `${width}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <EmptyState label={t("timing.noData", "No timing data yet.")} />
      )}
    </section>
  );
}

function buildDetectorTiming(
  result: AnomalyResult | null,
): Record<string, DetectorTiming> {
  const timingByDetector: Record<string, DetectorTiming> = {};
  const detectorTiming = result?.timing?.detectors;
  if (Array.isArray(detectorTiming)) {
    for (const timing of detectorTiming) {
      if (timing.detector) {
        timingByDetector[timing.detector] = timing;
      }
    }
  } else if (detectorTiming) {
    Object.assign(timingByDetector, detectorTiming);
  }

  for (const [name, output] of Object.entries(result?.detector_outputs ?? {})) {
    if (typeof output.duration_ms !== "number") {
      continue;
    }
    timingByDetector[name] = {
      ...timingByDetector[name],
      detector: name,
      duration_ms: output.duration_ms,
      status: timingByDetector[name]?.status ?? output.status,
    };
  }

  return timingByDetector;
}

function buildDetectorNames(
  detectors: DetectorResponse[],
  result: AnomalyResult | null,
  timingByDetector: Record<string, DetectorTiming>,
): string[] {
  const names = new Set(
    detectors.length > 0
      ? visibleDetectors(detectors).map((detector) => detector.name)
      : defaultDetectorNames,
  );
  for (const name of Object.keys(result?.detector_outputs ?? {})) {
    if (isVisibleDetectorName(name)) {
      names.add(name);
    }
  }
  for (const name of Object.keys(timingByDetector)) {
    if (isVisibleDetectorName(name)) {
      names.add(name);
    }
  }
  return [...names];
}

function detectorDurationMs(
  result: AnomalyResult | null,
  timingByDetector: Record<string, DetectorTiming>,
  name: string,
): number | null {
  return (
    timingByDetector[name]?.duration_ms ??
    result?.detector_outputs[name]?.duration_ms ??
    null
  );
}

function detectorStatusLabel(
  status: string | null | undefined,
  t: (key: string, fallback?: string) => string,
): string {
  if (!status) {
    return t("timing.noDataShort", "no data");
  }
  return t(`status.${status}`, status);
}

function statusTone(status: string | null | undefined) {
  if (status === "ready" || status === "completed") {
    return "success";
  }
  if (status === "not_ready") {
    return "warning";
  }
  return "neutral";
}

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}
