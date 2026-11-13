import { useNavigate } from "react-router";
import type { Dashboard, DetailMetric } from "../../core/gateways/reportingContract";
import { shopPath } from "../../core/profile/shopProfile";
import { ListCard, ListCardRow } from "../../shared/ui";
import { STOCK_KEY } from "../catalog/catalogRights";
import { stockViewPath, VIEW as STOCK_VIEW } from "../stock/stockNav";
import { count, laterLot, valueRow } from "./homeText";
import { useShownBlock } from "./moduleBlock";
import { ReceivablesSection, TrucksSection } from "./ModuleSections";
import { Section } from "./Section";
import { warn } from "./warnBadge";

interface Props {
  shopId: string;
  dashboard: Dashboard;
  open: (metric: DetailMetric) => void;
}

/** Stock (module `catalog`, toujours actif) ; « Déplacements en route » : module `transfers`. */
function StockSection({ shopId, stock, open }: Props & { stock: Dashboard["stock"] }) {
  const navigate = useNavigate();
  const shown = useShownBlock();
  const inTransit = shown(stock.in_transit, "transfers");
  const value = valueRow(stock.value);
  const damaged = valueRow(stock.damaged);
  return (
    <Section title="Stock">
      <ListCard label="Stock">
        <ListCardRow
          title="Valeur du stock"
          subtitle={`${value.note}, hors stock abîmé${inTransit === null ? "" : " et en route"}`}
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
        {inTransit !== null && (
          <ListCardRow title="Déplacements en route" subtitle={laterLot(inTransit)} />
        )}
      </ListCard>
    </Section>
  );
}

/**
 * UC-TDB-01 points 3 à 5 : créances, stock, camions (états actuels ; Lot 2 annoncé). Le bloc
 * d'un module éteint (`null`, specs § 15.1) n'apparaît pas, ni à zéro.
 */
export function StateBlocks({ shopId, dashboard, open }: Props) {
  const shown = useShownBlock();
  const receivables = shown(dashboard.receivables, "receivables");
  const trucks = shown(dashboard.trucks, "transport");
  return (
    <>
      {receivables !== null && (
        <ReceivablesSection
          shopId={shopId}
          receivables={receivables}
          period={dashboard.period}
          open={open}
        />
      )}
      <StockSection shopId={shopId} dashboard={dashboard} stock={dashboard.stock} open={open} />
      {trucks !== null && <TrucksSection trucks={trucks} />}
    </>
  );
}
