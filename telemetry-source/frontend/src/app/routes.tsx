import type { LucideIcon } from "lucide-react";
import { Activity, Database, RadioTower, SatelliteDish } from "lucide-react";
import type { ReactElement } from "react";

import { ExternalPage } from "../pages/ExternalPage";
import { SnapshotPage } from "../pages/SnapshotPage";
import { StreamsPage } from "../pages/StreamsPage";
import { SyntheticPage } from "../pages/SyntheticPage";

export type RouteId = "synthetic" | "snapshot" | "external" | "streams";

export type AppRoute = {
  id: RouteId;
  labelKey: string;
  fallbackLabel: string;
  icon: LucideIcon;
  element: ReactElement;
};

export const routes: AppRoute[] = [
  {
    id: "synthetic",
    labelKey: "routes.synthetic",
    fallbackLabel: "Synthetic generator",
    icon: SatelliteDish,
    element: <SyntheticPage />,
  },
  {
    id: "snapshot",
    labelKey: "routes.snapshot",
    fallbackLabel: "Snapshot",
    icon: Database,
    element: <SnapshotPage />,
  },
  {
    id: "external",
    labelKey: "routes.external",
    fallbackLabel: "External source",
    icon: RadioTower,
    element: <ExternalPage />,
  },
  {
    id: "streams",
    labelKey: "routes.streams",
    fallbackLabel: "Streams",
    icon: Activity,
    element: <StreamsPage />,
  },
];
