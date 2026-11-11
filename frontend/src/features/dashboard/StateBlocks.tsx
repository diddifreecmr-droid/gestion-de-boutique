import { useNavigate } from "react-router";
import type { Dashboard, DetailMetric } from "../../core/gateways/reportingContract";
import { shopPath } from "../../core/profile/shopProfile";
import { Badge, ListCard, ListCardRow } from "../../shared/ui";
import { STOCK_KEY } from "../catalog/catalogRights";
import { RECEIVABLES_KEY } from "../receivables/receivablesNav";
import { stockViewPath, VIEW as STOCK_VIEW } from "../stock/stockNav";
import { count, laterLot, valueRow } from "./homeText";
import { figureLabel, kindOf } from "./periods";
import { Section } from "./Section";

interface Props {
  shopId: string;
  dashboard: Dashboard;
  open: (metric: DetailMetric) => void;
}

/** UC-TDB-01 points 3 à 5 : créances, stock, camions (états actuels ; Lot 2 annoncé). */
export function StateBlocks({ shopId, dashboard, open }: Props) {
  const navigate = useNavigate();
  const { receivables, stock, trucks } = dashboard;
  const value = valueRow(stock.value);
  const damaged = valueRow(stock.damaged);
  const warn = (n: number, word: string) =>
    n > 0 ? { badge: <Badge status="warning">{word}</Badge> } : {};
  return (
    <>
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
            title={figureLabel("Versements reçus", kindOf(dashboard.period))}
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
      <Section title="Stock">
        <ListCard label="Stock">
          <ListCardRow
            title="Valeur du stock"
            subtitle={`${value.note}, hors stock abîmé et en route`}
            {...(value.amount === undefined ? {} : { amount: value.amount })}
            onOpen={() => void navigate(stockViewPath(shopId, STOCK_VIEW.value))}
          />
          <ListCardRow
            title="Stock abîmé"
            subtitle={damaged.note}
            {...(damaged.amount === undefined ? {} : { amount: damaged.amount })}
            onOpen={() => void navigate(stockViewPath(shopId, STOCK_VIEW.damaged))}
          />
          <ListCardRow
            title="Stock bas"
            subtitle={count(stock.low_stock, "article sous le seuil", "articles sous le seuil")}
            {...warn(stock.low_stock, "Stock bas")}
            onOpen={() => {
              open("low_stock");
            }}
          />
          <ListCardRow
            title="Stock à vérifier"
            subtitle={count(stock.to_verify, "quantité négative", "quantités négatives")}
            {...warn(stock.to_verify, "À vérifier")}
            onOpen={() => void navigate(shopPath(shopId, STOCK_KEY))}
          />
          <ListCardRow title="Déplacements en route" subtitle={laterLot(stock.in_transit)} />
        </ListCard>
      </Section>
      <Section title="Camions">
        <ListCard label="Camions">
          <ListCardRow title="Camions en voyage ou en panne" subtitle={laterLot(trucks.trucks)} />
          <ListCardRow
            title="Dépenses de transport"
            subtitle={laterLot(trucks.transport_expenses)}
          />
        </ListCard>
      </Section>
    </>
  );
}
