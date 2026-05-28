import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  Activity,
  Gauge,
  RadioReceiver,
  RadioTower,
  RefreshCw,
  SatelliteDish,
} from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";

import { DashboardPage } from "../pages/DashboardPage";
import { ListenersPage } from "../pages/ListenersPage";
import { getAnalysisHealth } from "../shared/api/analysisServiceClient";
import { getTelemetrySourceHealth } from "../shared/api/telemetrySourceClient";
import { I18nProvider, useI18n } from "../shared/i18n/I18nProvider";
import { StatusPill } from "../shared/ui/StatusPill";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

type RouteId = "analysis" | "listeners";

const routes = [
  {
    id: "analysis",
    labelKey: "routes.analysis",
    fallbackLabel: "Analysis",
    titleKey: "analysis.title",
    fallbackTitle: "Analysis",
    kickerKey: "analysis.kicker",
    fallbackKicker: "Telemetry analysis",
    capabilities: [
      ["analysis.capability.state", "session state"],
      ["analysis.capability.profile", "analysis profile"],
      ["analysis.capability.outputs", "detector outputs"],
    ],
    icon: Activity,
    element: <DashboardPage />,
  },
  {
    id: "listeners",
    labelKey: "routes.listeners",
    fallbackLabel: "Listeners",
    titleKey: "listeners.title",
    fallbackTitle: "Listeners",
    kickerKey: "listeners.kicker",
    fallbackKicker: "Telemetry transport",
    capabilities: [
      ["listeners.capability.udp", "UDP listener"],
      ["listeners.capability.mavlink", "MAVLink ingress"],
      ["listeners.capability.metrics", "transport metrics"],
    ],
    icon: RadioReceiver,
    element: <ListenersPage />,
  },
] as const;

function Shell() {
  const [activeRouteId, setActiveRouteId] = useState<RouteId>("analysis");
  const { language, languages, setLanguage, t } = useI18n();
  const activeRoute = useMemo(
    () => routes.find((route) => route.id === activeRouteId) ?? routes[0],
    [activeRouteId],
  );
  const analysisHealthQuery = useQuery({
    queryKey: ["analysis-health"],
    queryFn: getAnalysisHealth,
    refetchInterval: 5000,
  });
  const sourceHealthQuery = useQuery({
    queryKey: ["telemetry-source-health"],
    queryFn: getTelemetrySourceHealth,
    refetchInterval: 5000,
  });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              <Gauge size={23} strokeWidth={2.4} />
            </span>
            <div>
              <strong>{t("app.title", "Telemetry Viewer")}</strong>
              <span>{t("app.subtitle", "Analysis dashboard")}</span>
            </div>
          </div>

          <div className="language-switcher" aria-label={t("language.label", "Language")}>
            {languages.map((item) => (
              <button
                className={item.code === language ? "active" : ""}
                key={item.code}
                onClick={() => setLanguage(item.code)}
                title={item.label}
                type="button"
              >
                {item.code.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <nav
          className="navigation"
          aria-label={t("app.primaryNavigation", "Primary navigation")}
        >
          {routes.map((route) => {
            const Icon = route.icon;
            return (
              <button
                className={route.id === activeRouteId ? "nav-item active" : "nav-item"}
                key={route.id}
                onClick={() => setActiveRouteId(route.id)}
                type="button"
              >
                <Icon size={18} />
                <span>{t(route.labelKey, route.fallbackLabel)}</span>
              </button>
            );
          })}
        </nav>

        <section className="health-stack" aria-label={t("app.services", "Services")}>
          <ServiceHealth
            icon={<RadioTower size={17} />}
            label={t("app.analysisService", "Analysis service")}
            onRefresh={() => void analysisHealthQuery.refetch()}
            status={analysisHealthQuery.data?.status}
          />
          <ServiceHealth
            icon={<SatelliteDish size={17} />}
            label={t("app.generatorApi", "Generator API")}
            onRefresh={() => void sourceHealthQuery.refetch()}
            status={sourceHealthQuery.data?.status}
          />
        </section>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <span className="section-kicker">
              {t(activeRoute.kickerKey, activeRoute.fallbackKicker)}
            </span>
            <h1>{t(activeRoute.titleKey, activeRoute.fallbackTitle)}</h1>
          </div>
          <div className="workspace-actions">
            <div className="capability-stack" aria-label="Viewer capabilities">
              <div className="capability-row">
                {activeRoute.capabilities.map(([key, fallback]) => (
                  <span className="capability-chip selected" key={key}>
                    {t(key, fallback)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </header>

        {activeRoute.element}
      </main>
    </div>
  );
}

function ServiceHealth({
  icon,
  label,
  onRefresh,
  status,
}: {
  icon: ReactNode;
  label: string;
  onRefresh: () => void;
  status: string | undefined;
}) {
  const { t } = useI18n();

  return (
    <div className="health-panel">
      <div className="health-title">
        <span className="health-icon" aria-hidden="true">
          {icon}
        </span>
        <span>{label}</span>
      </div>
      <div className="health-actions">
        <StatusPill
          tone={status === "ok" ? "success" : "danger"}
          label={status ?? t("app.unavailable", "unavailable")}
        />
        <button className="icon-button" onClick={onRefresh} type="button">
          <RefreshCw size={17} />
        </button>
      </div>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <Shell />
      </I18nProvider>
    </QueryClientProvider>
  );
}
