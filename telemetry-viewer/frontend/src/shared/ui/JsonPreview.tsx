import { useI18n } from "../i18n/I18nProvider";
import { normalizeDisplayValue } from "./display";

type JsonPreviewProps = {
  value: unknown;
};

export function JsonPreview({ value }: JsonPreviewProps) {
  const { t } = useI18n();
  return (
    <pre className="json-preview">
      {JSON.stringify(normalizeDisplayValue(value, t), null, 2)}
    </pre>
  );
}
