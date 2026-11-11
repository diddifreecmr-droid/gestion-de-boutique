import type { Dashboard, DetailMetric } from "../../core/gateways/reportingContract";
import { formatMoney } from "../../shared/format";
import { Badge, Disclosure, ListCard, ListCardRow } from "../../shared/ui";
import { count } from "./homeText";
import { Kpi } from "./Kpi";
import { figureLabel, kindOf, percentText } from "./periods";

interface Props {
  dashboard: Dashboard;
  open: (metric: DetailMetric) => void;
}

/** Écart signé « +40 000 FCFA » / « −12 000 FCFA » / « 0 FCFA ». */
function signed(amount: number): string {
  return amount > 0 ? `+${formatMoney(amount)}` : formatMoney(amount);
}

/** UC-TDB-03 : marge au CMP à côté de la marge au dernier coût, avec l'écart. */
function MarginAtWac({ dashboard }: { dashboard: Dashboard }) {
  const { margin, margin_wac: wac, margin_gap: gap } = dashboard.summary;
  const rows = [
    ["Marge au dernier coût", formatMoney(margin.value)],
    ["Marge au CMP", formatMoney(wac.value)],
    ["Écart (CMP − dernier coût)", signed(gap)],
  ] as const;
  return (
    <Disclosure label="Voir aussi au CMP">
      <dl className="m-0 flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
        {rows.map(([label, value]) => (
          <div key={label} className="flex flex-wrap items-baseline justify-between gap-2">
            <dt className="text-body text-text-muted">{label}</dt>
            <dd className="m-0 text-lead tabular-nums text-text">{value}</dd>
          </div>
        ))}
      </dl>
    </Disclosure>
  );
}

/** UC-TDB-01 point 1 : ventes (montant et nombre), argent encaissé, marge — gros chiffres. */
export function DayFigures({ dashboard, open }: Props) {
  const { summary, period } = dashboard;
  const kind = kindOf(period);
  const rate =
    summary.margin_rate_pct === null
      ? "Taux de marge non calculable"
      : `Taux de marge : ${percentText(summary.margin_rate_pct)}`;
  return (
    <section aria-label="Chiffres clés" className="flex flex-col gap-4">
      <Kpi
        label={figureLabel("Ventes", kind)}
        value={summary.sales}
        period={period}
        detail={count(summary.sales_count.value, "vente", "ventes", "Aucune vente")}
        onOpen={() => {
          open("sales");
        }}
      />
      <Kpi
        label={figureLabel("Argent encaissé", kind)}
        value={summary.collected}
        period={period}
        onOpen={() => {
          open("payments");
        }}
      />
      <Kpi
        label={figureLabel("Marge", kind)}
        value={summary.margin}
        period={period}
        detail={rate}
        onOpen={() => {
          open("sales");
        }}
      />
      <MarginAtWac dashboard={dashboard} />
      {summary.without_cost > 0 && (
        <ListCard label="Ventes sans coût connu">
          <ListCardRow
            title={count(summary.without_cost, "vente sans coût connu", "ventes sans coût connu")}
            subtitle="Leur marge n'est pas comptée"
            badge={<Badge status="warning">À vérifier</Badge>}
            onOpen={() => {
              open("sales");
            }}
          />
        </ListCard>
      )}
    </section>
  );
}
