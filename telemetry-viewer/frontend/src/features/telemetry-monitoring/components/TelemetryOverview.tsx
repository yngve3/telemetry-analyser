import type { AnomalyResult } from "../../../shared/contracts/anomalyResult";
import type { TelemetryPayload } from "../../../shared/contracts/telemetry";
import { useI18n } from "../../../shared/i18n/I18nProvider";
import {
  formatBoolean,
  formatInteger,
  formatNumber,
  formatText,
} from "../../../shared/ui/format";
import { Metric } from "../../../shared/ui/Metric";
import { StatusPill } from "../../../shared/ui/StatusPill";

type TelemetryOverviewProps = {
  result: AnomalyResult | null;
  telemetry: TelemetryPayload | null;
};

export function TelemetryOverview({ result, telemetry }: TelemetryOverviewProps) {
  const { t } = useI18n();

  return (
    <section className="data-panel">
      <div className="panel-header">
        <h2>{t("telemetry.title", "Telemetry overview")}</h2>
        <StatusPill
          label={
            telemetry
              ? t("telemetry.unified", "unified telemetry")
              : t("telemetry.metadata", "result metadata")
          }
          tone={telemetry ? "success" : "neutral"}
        />
      </div>
      <div className="panel-body">
        <div className="metric-grid telemetry-metrics">
          <Metric
            label={t("telemetry.droneId", "Drone ID")}
            value={formatText(telemetry?.drone_id ?? result?.drone_id)}
          />
          <Metric
            label={t("telemetry.timestamp", "Timestamp")}
            value={formatText(telemetry?.timestamp ?? result?.telemetry_timestamp)}
          />
          <Metric
            label={t("telemetry.altitude", "Altitude, m")}
            value={formatNumber(telemetry?.altitude_m, 1)}
          />
          <Metric
            label={t("telemetry.speed", "Speed, m/s")}
            value={formatNumber(telemetry?.ground_speed_m_s, 1)}
          />
          <Metric
            label={t("telemetry.battery", "Battery, %")}
            value={formatNumber(telemetry?.battery_percent, 0)}
          />
          <Metric
            label={t("telemetry.satellites", "Satellites")}
            value={formatInteger(telemetry?.satellites)}
          />
          <Metric
            label={t("telemetry.gpsFix", "GPS fix")}
            value={formatInteger(telemetry?.gps_fix_type)}
          />
          <Metric
            label={t("telemetry.flightMode", "Flight mode")}
            value={formatTranslatedValue(t, "flightMode", telemetry?.flight_mode)}
          />
          <Metric
            label={t("telemetry.armed", "Armed")}
            value={formatBoolean(
              telemetry?.armed,
              t("common.yes", "yes"),
              t("common.no", "no"),
            )}
          />
          <Metric
            label={t("telemetry.systemStatus", "System status")}
            value={formatTranslatedValue(t, "systemStatus", telemetry?.system_status)}
          />
          <Metric
            label={t("telemetry.heading", "Heading, deg")}
            value={formatNumber(telemetry?.heading_deg, 0)}
          />
          <Metric
            label={t("telemetry.verticalSpeed", "Vertical speed")}
            value={formatNumber(telemetry?.vertical_speed_m_s, 1)}
          />
        </div>
      </div>
    </section>
  );
}

function formatTranslatedValue(
  t: (key: string, fallback?: string) => string,
  prefix: string,
  value: string | null | undefined,
): string {
  const text = formatText(value);
  return text === "-" ? text : t(`${prefix}.${text}`, text);
}
