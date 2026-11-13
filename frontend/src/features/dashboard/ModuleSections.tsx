import { useNavigate } from "react-router";
import type { Dashboard, DetailMetric } from "../../core/gateways/reportingContract";
import { shopPath } from "../../core/profile/shopProfile";
import { ListCard, ListCardRow } from "../../shared/ui";
import { RECEIVABLES_KEY } from "../receivables/receivablesNav";
import { count } from "./homeText";
import { figureLabel, kindOf } from "./periods";
import { Section } from "./Section";
import { warn } from "./warnBadge";

type Receivables = NonNullable<Dashboard["receivables"]>;

/** Créances (module `receivables`) : affiché seulement si le bloc est reçu. */
export function ReceivablesSection({
  shopId,
  receivables,
  period,
  open,
}: {
  shopId: string;
  receivables: Receivables;
  period: Dashboard["period"];
  open: (metric: DetailMetric) => void;
}) {
  const navigate = useNavigate();
  return (
    <Section title="Créances">
      <ListCard label="Créances">
        <ListCardRow
          title="Total à recevoir"
          subtitle={count(receivables.debtor_count, "client débiteur", "clients débiteurs")}
          amount={receivables.total_due}
          onOpen={() => {
            open("receivables");
          }}
        />
        <ListCardRow
          title={figureLabel("Versements reçus", kindOf(period))}
          amount={receivables.received.value}
          onOpen={() => {
            open("payments");
          }}
        />
        <ListCardRow
          title="Rappels du jour"
          subtitle={count(
            receivables.reminders_due,
            "rappel à faire",
            "rappels à faire",
            "Aucun rappel aujourd'hui",
          )}
          {...warn(receivables.reminders_due, "À faire")}
          onOpen={() => void navigate(shopPath(shopId, RECEIVABLES_KEY))}
        />
      </ListCard>
    </Section>
  );
}
