import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { RadioTower, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";

import { routes, type RouteId } from "./routes";
import { getHealth } from "../shared/api/client";
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

function Shell() {
  const [activeRouteId, setActiveRouteId] = useState<RouteId>("synthetic");
  const { language, languages, setLanguage, t } = useI18n();
  const activeRoute = useMemo(
    () => routes.find((route) => route.id === activeRouteId) ?? routes[0],
    [activeRouteId],
  );
  const activeRouteLabel = t(activeRoute.labelKey, activeRoute.fallbackLabel);
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 5000,
  });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              <RadioTower size={23} strokeWidth={2.4} />
            </span>
            <div>
              <strong>{t("app.title", "Telemetry Source")}</strong>
              <span>{t("app.subtitle", "Control panel")}</span>
            </div>
          </div>

          <div className="language-switcher" aria-label={t("language.label", "Language")}>
            {languages.map((item) => (
              <button
                className={item.code === language ? "active" : ""}
                key={item.code}
                onClick={() => setLanguage(item.code)}
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

        <section className="health-panel" aria-label={t("app.backend", "Backend")}>
          <div>
            <span className="section-kicker">{t("app.backend", "Backend")}</span>
            <StatusPill
              tone={healthQuery.data?.status === "ok" ? "success" : "danger"}
              label={healthQuery.data?.status ?? t("app.unavailable", "unavailable")}
            />
          </div>
          <button
            className="icon-button"
            onClick={() => void healthQuery.refetch()}
            title={t("app.refreshBackend", "Refresh backend health")}
            type="button"
          >
            <RefreshCw size={17} />
          </button>
        </section>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <span className="section-kicker">{t("app.kicker", "Telemetry source")}</span>
            <h1>{activeRouteLabel}</h1>
          </div>
          <div className="workspace-actions">
            <div
              className="capability-stack"
              aria-label={t(
                "capability.telemetryCapabilities",
                "Telemetry capabilities",
              )}
            >
              <div
                className="capability-row"
                aria-label={t("capability.payloadFormat", "Payload format")}
              >
                <span className="capability-chip selected">
                  {t("capability.mavlink", "MAVLink")}
                </span>
                <button
                  className="capability-chip unavailable"
                  disabled
                  title={t(
                    "capability.jsonUnavailable",
                    "JSON output is not available in the backend yet",
                  )}
                  type="button"
                >
                  {t("capability.json", "JSON")}
                </button>
              </div>
              <div
                className="capability-row"
                aria-label={t("capability.transport", "Transport")}
              >
                <span className="capability-chip selected">
                  {t("capability.udp", "UDP")}
                </span>
                <button
                  className="capability-chip unavailable"
                  disabled
                  title={t(
                    "capability.websocketUnavailable",
                    "WebSocket transport is not available in the backend yet",
                  )}
                  type="button"
                >
                  {t("capability.websocket", "WebSocket")}
                </button>
              </div>
            </div>
          </div>
        </header>

        {activeRoute.element}
      </main>
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
