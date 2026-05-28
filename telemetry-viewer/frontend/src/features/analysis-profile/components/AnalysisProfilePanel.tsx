import type { AnalysisProfile } from "../../../shared/contracts/analysisProfile";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { JsonPreview } from "../../../shared/ui/JsonPreview";
import { StatusPill } from "../../../shared/ui/StatusPill";

type AnalysisProfilePanelProps = {
  error: Error | null;
  isLoading: boolean;
  isSaving: boolean;
  onChange: (profile: AnalysisProfile) => void;
  onSave: () => void;
  profile: AnalysisProfile | null;
};

export function AnalysisProfilePanel({
  error,
  isLoading,
  isSaving,
  onChange,
  onSave,
  profile,
}: AnalysisProfilePanelProps) {
  const { t } = useI18n();

  if (profile === null) {
    return (
      <section className="data-panel">
        <div className="panel-header">
          <h2>{t("profile.title", "Analysis profile")}</h2>
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

  function setProfile(patch: Partial<AnalysisProfile>) {
    onChange({ ...currentProfile, ...patch });
  }

  function updateEnabledRules(value: string) {
    const enabledRules = value
      .split(/[,\n]/)
      .map((item) => item.trim())
      .filter(Boolean);
    setProfile({ enabled_rules: enabledRules.length > 0 ? enabledRules : null });
  }

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("profile.title", "Analysis profile")}</h2>
        <StatusPill
          label={`${currentProfile.enabled_detectors.length} ${t("profile.enabled", "enabled")}`}
          tone={currentProfile.enabled_detectors.length > 0 ? "success" : "danger"}
        />
      </div>

      <div className="panel-body">
        <label className="field">
          <span>{t("profile.enabledRules", "Enabled rules")}</span>
          <textarea
            className="compact-textarea"
            spellCheck={false}
            value={profile.enabled_rules?.join(", ") ?? ""}
            onChange={(event) => updateEnabledRules(event.target.value)}
          />
        </label>

        <div className="form-grid">
          <label className="field">
            <span>{t("profile.historySize", "History size")}</span>
            <input
              min="1"
              type="number"
              value={profile.history_size}
              onChange={(event) =>
                setProfile({ history_size: Number(event.target.value) })
              }
            />
          </label>
          <label className="field">
            <span>{t("profile.modelWindowSize", "Model window size")}</span>
            <input
              min="1"
              type="number"
              value={profile.model_window_size}
              onChange={(event) =>
                setProfile({ model_window_size: Number(event.target.value) })
              }
            />
          </label>
          <label className="field">
            <span>{t("profile.mlArtifactPath", "ML artifact path")}</span>
            <input
              value={profile.ml_model_artifact_path ?? ""}
              onChange={(event) =>
                setProfile({
                  ml_model_artifact_path: emptyToNull(event.target.value),
                })
              }
            />
          </label>
          <label className="field">
            <span>{t("profile.nnArtifactPath", "NN artifact path")}</span>
            <input
              value={profile.nn_model_artifact_path ?? ""}
              onChange={(event) =>
                setProfile({
                  nn_model_artifact_path: emptyToNull(event.target.value),
                })
              }
            />
          </label>
        </div>

        <details className="json-details">
          <summary>{t("profile.thresholds", "Thresholds")}</summary>
          <JsonPreview value={profile.thresholds} />
        </details>

        <div className="button-row">
          <button
            className="primary-button"
            disabled={isSaving || currentProfile.enabled_detectors.length === 0}
            onClick={onSave}
            type="button"
          >
            {t("profile.save", "Save profile")}
          </button>
        </div>

        {error ? <div className="message error">{error.message}</div> : null}
      </div>
    </section>
  );
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}
