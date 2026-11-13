import type { Dashboard, DetailMetric } from "../../core/gateways/reportingContract";
import { formatMoney } from "../../shared/format";
import { Kpi } from "./Kpi";
import { useShownBlock } from "./moduleBlock";
import { figureLabel, kindOf } from "./periods";
import { Section } from "./Section";

/**
 * UC-TDB-01 point 2 : dépenses de la boutique et résultat simple (marge − dépenses, § 14.1).
 * Le résultat s'explique par ses deux termes, affichés juste au-dessus : il n'a pas de liste.
 * Sans le module `expenses` (`summary.expenses = null`) : ni dépenses ni résultat — le résultat
 * vaudrait la marge, déjà affichée ; aucune dépense « 0 » n'est inventée. Dans le tableau de
 * bord, la section est repliée ; son résumé donne les deux montants.
 */
export function ResultFigures({
  dashboard,
  open,
}: {
  dashboard: Dashboard;
  open: (metric: DetailMetric) => void;
}) {
  const shown = useShownBlock();
  const { summary, period } = dashboard;
  const expenses = shown(summary.expenses, "expenses");
  if (expenses === null) return null;
  const kind = kindOf(period);
  return (
    <Section
      title="Dépenses et résultat"
      summary={`Dépenses ${formatMoney(expenses.value)} · Résultat ${formatMoney(summary.result.value)}`}
    >
      <Kpi
        label={figureLabel("Dépenses", kind)}
        value={expenses}
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
    </Section>
  );
}
