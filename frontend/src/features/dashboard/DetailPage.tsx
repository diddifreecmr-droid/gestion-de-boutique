import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router";
import type { DetailMetric, PeriodQuery } from "../../core/gateways/reportingContract";
import { Button, EmptyState, ListCard, ListCardRow } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { useDashboardNav } from "./dashboardNav";
import { DETAIL_TITLES, detailRow, totalText } from "./detailRows";
import { FiguresPending } from "./FiguresOffline";
import { periodText, queryKey, resolveChoice } from "./periods";
import { useFigures, useReporting } from "./reportingContext";

function Lines({
  shopId,
  metric,
  query,
}: {
  shopId: string;
  metric: DetailMetric;
  query: PeriodQuery;
}) {
  const { gateway } = useReporting();
  const navigate = useNavigate();
  const { loaded, retry } = useFigures(`detail:${shopId}:${metric}:${queryKey(query)}`, () =>
    gateway.detail(shopId, metric, query),
  );
  if (loaded.status !== "ready") {
    return <FiguresPending status={loaded.status} onRetry={retry} label="Lecture de la liste…" />;
  }
  const detail = loaded.value;
  if (detail.metric !== metric) {
    throw new Error(`Détail « ${detail.metric} » reçu pour « ${metric} »`);
  }
  const rows = detail.lines.map((line) => detailRow(shopId, line));
  return (
    <>
      <p className="m-0 text-body text-text-muted">{periodText(detail.period)}</p>
      <p className="m-0 flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-surface p-4 shadow-card">
        <span className="text-label font-semibold text-text">Total</span>
        <span className="text-amount font-bold tabular-nums text-text">
          {totalText(metric, detail.total)}
        </span>
      </p>
      {rows.length === 0 ? (
        <EmptyState message="Rien à afficher sur cette période." />
      ) : (
        <ListCard label={DETAIL_TITLES[metric]}>
          {rows.map((row) => {
            const { href } = row;
            return (
              <ListCardRow
                key={row.key}
                title={row.title}
                subtitle={row.subtitle}
                {...(row.amount === undefined ? {} : { amount: row.amount })}
                {...(href === undefined ? {} : { onOpen: () => void navigate(href) })}
              />
            );
          })}
        </ListCard>
      )}
    </>
  );
}

/** UC-TDB-04 : la liste qui explique un chiffre, sur la période choisie ; retour à l'accueil. */
export function DetailPage({ shopId, metric }: { shopId: string; metric: DetailMetric }) {
  const { now } = useReporting();
  const nav = useDashboardNav();
  const resolved = resolveChoice(nav.choice, businessDate(now()));
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.close}>
        Retour à l'accueil
      </Button>
      <h1 className="m-0 text-title font-bold text-text">{DETAIL_TITLES[metric]}</h1>
      {"query" in resolved ? (
        <Lines shopId={shopId} metric={metric} query={resolved.query} />
      ) : (
        <EmptyState message={resolved.problem} />
      )}
    </>
  );
}
