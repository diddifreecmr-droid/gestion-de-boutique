import { ArrowLeftRight, ClipboardList, Receipt, ShoppingCart } from "lucide-react";
import { useNavigate } from "react-router";
import { useModules } from "../../core/profile/modulesContext";
import { shopPath } from "../../core/profile/shopProfile";
import { ActionTile, ActionTileGrid, Badge, Button, ListCard, ListCardRow } from "../../shared/ui";
import { STOCK_KEY } from "../catalog/catalogRights";
import { EXPENSES_KEY, VIEW as EXPENSE_VIEW } from "../expenses/expenseNav";
import { PURCHASES_KEY, VIEW as PURCHASE_VIEW } from "../purchasing/purchasingNav";
import { stockViewPath, VIEW as STOCK_VIEW } from "../stock/stockNav";
import { FiguresPending } from "./FiguresOffline";
import { count, laterLot, valueRow } from "./homeText";
import { useShownBlock } from "./moduleBlock";
import { useHome } from "./useHome";

/** Raison affichée sur « Déplacer du stock » : les déplacements arrivent au Lot 2. */
const TRANSFERS_LATER = "Disponible au Lot 2";

function AccountantFigures({ shopId }: { shopId: string }) {
  const navigate = useNavigate();
  const shown = useShownBlock();
  const { loaded, retry } = useHome(shopId, "accountant");
  if (loaded.status !== "ready") return <FiguresPending status={loaded.status} onRetry={retry} />;
  const home = loaded.value;
  const value = valueRow(home.stock_value);
  const toReceive = shown(home.transfers_to_receive, "transfers");
  const expenses = shown(home.expenses, "expenses");
  return (
    <ListCard label="Ma journée">
      {toReceive !== null && (
        <ListCardRow title="Déplacements à réceptionner" subtitle={laterLot(toReceive)} />
      )}
      <ListCardRow
        title="Alertes de stock"
        subtitle={count(home.low_stock, "article sous le seuil", "articles sous le seuil")}
        {...(home.low_stock > 0 ? { badge: <Badge status="warning">Stock bas</Badge> } : {})}
        onOpen={() => void navigate(shopPath(shopId, STOCK_KEY))}
      />
      <ListCardRow
        title="Valeur du stock"
        subtitle={value.note}
        {...(value.amount === undefined ? {} : { amount: value.amount })}
        onOpen={() => void navigate(stockViewPath(shopId, STOCK_VIEW.value))}
      />
      {expenses !== null && (
        <ListCardRow
          title="Dépenses du jour"
          amount={expenses}
          onOpen={() => void navigate(shopPath(shopId, EXPENSES_KEY))}
        />
      )}
    </ListCard>
  );
}

/**
 * Accueil du comptable (UC-TDB-05) : Achat, Dépense, Inventaire ; « Déplacer du stock » au
 * Lot 2 ; puis ses chiffres. Le bloc `accountant` de `GET /home` n'a aucune vente ni chiffre
 * d'affaires (RG-D03) : rien de tel n'est affiché. Chaque tuile, bouton ou ligne d'un module
 * éteint (`purchases`, `expenses`, `transfers`) disparaît (specs § 15.1).
 */
export function AccountantHome({ shopId }: { shopId: string }) {
  const navigate = useNavigate();
  const modules = useModules();
  return (
    <>
      <ActionTileGrid>
        {modules.has("purchases") && (
          <ActionTile
            icon={ShoppingCart}
            label="Achat"
            onClick={() =>
              void navigate(`${shopPath(shopId, PURCHASES_KEY)}?vue=${PURCHASE_VIEW.create}`)
            }
          />
        )}
        {modules.has("expenses") && (
          <ActionTile
            icon={Receipt}
            label="Dépense"
            onClick={() =>
              void navigate(`${shopPath(shopId, EXPENSES_KEY)}?vue=${EXPENSE_VIEW.create}`)
            }
          />
        )}
        <ActionTile
          icon={ClipboardList}
          label="Inventaire"
          onClick={() => void navigate(stockViewPath(shopId, STOCK_VIEW.inventory))}
        />
      </ActionTileGrid>
      {modules.has("transfers") && (
        <Button
          variant="secondary"
          fullWidth
          icon={ArrowLeftRight}
          disabledReason={TRANSFERS_LATER}
        >
          Déplacer du stock
        </Button>
      )}
      <AccountantFigures shopId={shopId} />
    </>
  );
}
