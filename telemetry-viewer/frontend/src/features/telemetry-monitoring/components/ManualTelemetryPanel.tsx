import { Play } from "lucide-react";

import { useI18n } from "../../../shared/i18n/I18nProvider";

type ManualTelemetryPanelProps = {
  error: Error | null;
  isAnalyzing: boolean;
  onAnalyze: () => void;
  onTelemetryTextChange: (value: string) => void;
  parseError: string | null;
  telemetryText: string;
};

export function ManualTelemetryPanel({
  error,
  isAnalyzing,
  onAnalyze,
  onTelemetryTextChange,
  parseError,
  telemetryText,
}: ManualTelemetryPanelProps) {
  const { t } = useI18n();

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("manual.title", "Manual telemetry")}</h2>
      </div>
      <div className="panel-body">
        <label className="field">
          <span>{t("manual.json", "Unified telemetry JSON")}</span>
          <textarea
            spellCheck={false}
            value={telemetryText}
            onChange={(event) => onTelemetryTextChange(event.target.value)}
          />
        </label>
        <div className="button-row">
          <button
            className="primary-button"
            disabled={isAnalyzing}
            onClick={onAnalyze}
            type="button"
          >
            <Play size={16} />
            {t("manual.analyze", "Analyze sample")}
          </button>
        </div>
        {parseError ? <div className="message error">{parseError}</div> : null}
        {error ? <div className="message error">{error.message}</div> : null}
      </div>
    </section>
  );
}
