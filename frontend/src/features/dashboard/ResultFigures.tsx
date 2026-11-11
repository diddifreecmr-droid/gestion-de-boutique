import type { Dashboard, DetailMetric } from "../../core/gateways/reportingContract";
import { Kpi } from "./Kpi";
import { figureLabel, kindOf } from "./periods";

/**
 * UC-TDB-01 point 2 : dépenses de la boutique et résultat simple (marge − dépenses, § 14.1).
 * Le résultat s'explique par ses deux termes, affichés juste au-dessus : il n'a pas de liste.
 */
export function ResultFigures({
  dashboard,
  open,
}: {
  dashboard: Dashboard;
  open: (metric: DetailMetric) => void;
}) {
  const { summary, period } = dashboard;
  const kind = kindOf(period);
  return (
    <section aria-label="Dépenses et résultat" className="flex flex-col gap-4">
      <Kpi
        label={figureLabel("Dépenses", kind)}
        value={summary.expenses}
        period={period}
        onOpen={() => {
          open("expenses");
        }}
      />
      <Kpi
        label={figureLabel("Résultat simple", kind)}
        value={summary.result}
        period={period}
        detail="Marge − dépenses"
      />
    </section>
  );
}
