import type {
  AnalysisProfile,
  DetectorResponse,
} from "../../../shared/contracts/analysisProfile";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import {
  formatDetectorName,
  isVisibleDetectorName,
  supportedAnalyzerNames,
  visibleDetectors,
} from "../../../shared/ui/display";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { StatusPill } from "../../../shared/ui/StatusPill";

type DetectorSelectorPanelProps = {
  detectors: DetectorResponse[];
  error: Error | null;
  isLoading: boolean;
  isSaving: boolean;
  onChange: (profile: AnalysisProfile) => void;
  onSave: () => void;
  profile: AnalysisProfile | null;
};

const fallbackDetectors: DetectorResponse[] = [
  {
    name: "rule_based",
    implementation: "RuleBasedDetector",
    kind: "rule_based",
    status: "available",
    detector_name: "rule_based",
    connected: true,
    description: "Known critical telemetry conditions.",
    aliases: [],
  },
  {
    name: "correlation_based",
    implementation: "CorrelationBasedDetector",
    kind: "model_based",
    status: "available",
    detector_name: "correlation_based",
    connected: true,
    description: "Parameter consistency checks.",
    aliases: ["correlation"],
  },
  {
    name: "isolation_forest",
    implementation: "IsolationForestDetector",
    kind: "model_based",
    status: "available",
    detector_name: "isolation_forest",
    connected: true,
    description: "Main ML analyzer.",
    aliases: ["isolationforest"],
  },
  {
    name: "autoencoder",
    implementation: "AutoencoderDetector",
    kind: "model_based",
    status: "available",
    detector_name: "autoencoder",
    connected: true,
    description: "Experimental additional analyzer.",
    aliases: ["nn", "neural_network"],
  },
];

export function DetectorSelectorPanel({
  detectors,
  error,
  isLoading,
  isSaving,
  onChange,
  onSave,
  profile,
}: DetectorSelectorPanelProps) {
  const { t } = useI18n();

  if (profile === null) {
    return (
      <section className="data-panel">
        <div className="panel-header">
          <h2>{t("detectorSelector.title", "Analyzers")}</h2>
          <StatusPill
            label={
              isLoading
                ? t("profile.loading", "loading")
                : t("profile.unavailable", "unavailable")
            }
          />
        </div>
        <EmptyState label={t("profile.notLoaded", "Profile is not loaded.")} />
      </section>
    );
  }

  const currentProfile = profile;
  const availableDetectors = visibleDetectors(
    detectors.length > 0 ? detectors : fallbackDetectors,
  );
  const visibleEnabledDetectors =
    currentProfile.enabled_detectors.filter(isVisibleDetectorName);
  const enabled = new Set(visibleEnabledDetectors);

  function toggleDetector(name: string) {
    const nextEnabled = new Set(enabled);
    if (nextEnabled.has(name)) {
      nextEnabled.delete(name);
    } else {
      nextEnabled.add(name);
    }
    const enabledAnalyzers = supportedAnalyzerNames.filter((item) =>
      nextEnabled.has(item),
    );
    onChange({
      ...currentProfile,
      enabled_models: enabledAnalyzers,
      enabled_detectors: enabledAnalyzers,
    });
  }

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("detectorSelector.title", "Analyzers")}</h2>
        <StatusPill
          label={`${visibleEnabledDetectors.length} ${t("detectorSelector.selected", "selected")}`}
          tone={visibleEnabledDetectors.length > 0 ? "success" : "danger"}
        />
      </div>

      <div className="panel-body">
        <div className="detector-chip-grid">
          {availableDetectors.map((detector) => {
            const isEnabled = enabled.has(detector.name);
            return (
              <button
                aria-pressed={isEnabled}
                className={isEnabled ? "detector-chip active" : "detector-chip"}
                disabled={isSaving}
                key={detector.name}
                onClick={() => toggleDetector(detector.name)}
                type="button"
              >
                <strong>{formatDetectorName(detector.name, t)}</strong>
                <small>{detectorDescription(detector, t)}</small>
                <span>{t(`status.${detector.status}`, detector.status)}</span>
              </button>
            );
          })}
        </div>

        <div className="button-row">
          <button
            className="primary-button"
            disabled={isSaving || visibleEnabledDetectors.length === 0}
            onClick={onSave}
            type="button"
          >
            {t("detectorSelector.save", "Save analyzers")}
          </button>
        </div>

        {error ? <div className="message error">{error.message}</div> : null}
      </div>
    </section>
  );
}

function detectorDescription(detector: DetectorResponse, t: ReturnType<typeof useI18n>["t"]) {
  return t(`detectorDescription.${detector.name}`, detector.description);
}
