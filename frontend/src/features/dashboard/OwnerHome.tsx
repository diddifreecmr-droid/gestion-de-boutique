import type { PeriodQuery } from "../../core/gateways/reportingContract";
import { businessDate } from "../expenses/businessDay";
import { AlertsSection } from "./AlertsSection";
import { useDashboardNav, type DashboardNav } from "./dashboardNav";
import { DayBars } from "./DayBars";
import { DayFigures } from "./DayFigures";
import { FIGURES_OFFLINE, FiguresPending } from "./FiguresOffline";
import { periodText, queryKey, resolveChoice } from "./periods";
import { PeriodPicker } from "./PeriodPicker";
import { useFigures, useReporting } from "./reportingContext";
import { ResultFigures } from "./ResultFigures";
import { StateBlocks } from "./StateBlocks";

function Figures({
  shopId,
  query,
  nav,
}: {
  shopId: string;
  query: PeriodQuery;
  nav: DashboardNav;
}) {
  const { gateway } = useReporting();
  const { loaded, retry } = useFigures(`dashboard:${shopId}:${queryKey(query)}`, () =>
    gateway.dashboard(shopId, query),
  );
  if (loaded.status !== "ready") {
    return (
      <>
        <FiguresPending status={loaded.status} onRetry={retry} />
        <AlertsSection
          shopId={shopId}
          errorReports={loaded.status === "loading" ? "Lecture…" : FIGURES_OFFLINE}
        />
      </>
    );
  }
  const dashboard = loaded.value;
  return (
    <>
      <p className="m-0 text-body text-text-muted">{periodText(dashboard.period)}</p>
      <DayFigures dashboard={dashboard} open={nav.open} />
      <ResultFigures dashboard={dashboard} open={nav.open} />
      {dashboard.series !== null && <DayBars series={dashboard.series} />}
      <StateBlocks shopId={shopId} dashboard={dashboard} open={nav.open} />
      <AlertsSection shopId={shopId} errorReports={dashboard.alerts.error_reports} />
    </>
  );
}

/**
 * Accueil du propriétaire (UC-TDB-01 à 04, design-system § 7.2) : période en haut, gros
 * chiffres, puis créances, stock, camions et alertes. Hors connexion : « Chiffres disponibles
 * avec internet » à la place des montants (RG-T25).
 */
export function OwnerHome({ shopId }: { shopId: string }) {
  const { now } = useReporting();
  const nav = useDashboardNav();
  const today = businessDate(now());
  const resolved = resolveChoice(nav.choice, today);
  return (
    <>
      <PeriodPicker
        nav={nav}
        today={today}
        problem={"problem" in resolved ? resolved.problem : undefined}
      />
      {"query" in resolved ? (
        <Figures shopId={shopId} query={resolved.query} nav={nav} />
      ) : (
        <AlertsSection shopId={shopId} errorReports="Choisissez une période valable" />
      )}
    </>
  );
}
