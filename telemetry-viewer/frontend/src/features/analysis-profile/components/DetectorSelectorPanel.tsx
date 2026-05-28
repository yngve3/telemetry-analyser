import type {
  AnalysisProfile,
  DetectorResponse,
} from "../../../shared/contracts/analysisProfile";
import { useI18n } from "../../../shared/i18n/I18nProvider";
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
  { name: "rule_based", kind: "rule_based", status: "available", aliases: [] },
  { name: "ml", kind: "ml", status: "requires_artifact", aliases: [] },
  {
    name: "nn_autoencoder",
    kind: "nn",
    status: "requires_artifact",
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
  const availableDetectors = detectors.length > 0 ? detectors : fallbackDetectors;
  const enabled = new Set(currentProfile.enabled_detectors);

  function toggleDetector(name: string) {
    const nextEnabled = new Set(enabled);
    if (nextEnabled.has(name)) {
      nextEnabled.delete(name);
    } else {
      nextEnabled.add(name);
    }
    onChange({ ...currentProfile, enabled_detectors: Array.from(nextEnabled) });
  }

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("detectorSelector.title", "Analyzers")}</h2>
        <StatusPill
          label={`${currentProfile.enabled_detectors.length} ${t("detectorSelector.selected", "selected")}`}
          tone={currentProfile.enabled_detectors.length > 0 ? "success" : "danger"}
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
                <strong>{detector.name}</strong>
                <span>{t(`status.${detector.status}`, detector.status)}</span>
              </button>
            );
          })}
        </div>

        <div className="button-row">
          <button
            className="primary-button"
            disabled={isSaving || currentProfile.enabled_detectors.length === 0}
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
