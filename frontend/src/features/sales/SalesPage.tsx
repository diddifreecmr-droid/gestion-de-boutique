import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useSearchParams } from "react-router";
import { useGateways } from "../../core/gateways/gateways";
import type { ExchangeRules } from "../../core/profile/types";
import { useSignedIn } from "../../core/services/servicesContext";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { ReturnPage } from "./returns/ReturnPage";
import { SaleDetail } from "./SaleDetail";
import { SaleList } from "./SaleList";
import { loadSaleRefs } from "./saleRefs";
import type { SaleRole } from "./salesNav";
import { useLookup } from "./useLookup";

/** Vue « Retour ou échange » (`?id=…&vue=retour`) : propriétaire ; employé autorisé : échange. */
export const RETURN_VIEW = "retour";

/** Section des ventes (UC-VEN-05 à 08) : liste du jour, fiche `?id=`, reçu, annulation. */
export function SalesPage({
  shopId,
  role,
  title,
  exchange,
}: {
  shopId: string;
  role: SaleRole;
  title: string;
  exchange: ExchangeRules;
}) {
  const me = useSignedIn();
  const gateways = useGateways();
  const [params, setParams] = useSearchParams();
  const [round, setRound] = useState(0);
  const rulesKey = `${String(exchange.days)}:${String(exchange.employeeAllowed)}`;
  const refs = useLookup(`${shopId}:${String(round)}:${rulesKey}`, () =>
    loadSaleRefs(gateways, shopId, { role, userId: me.userId, exchange }),
  );
  if (refs.status !== "ready") {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">{title}</h1>
        {refs.status === "loading" ? (
          <Skeleton lines={4} label="Chargement des ventes…" />
        ) : (
          <EmptyState
            message="Connexion nécessaire pour afficher les ventes."
            action={
              <Button
                variant="secondary"
                icon={RefreshCw}
                onClick={() => {
                  setRound((n) => n + 1);
                }}
              >
                Réessayer
              </Button>
            }
          />
        )}
      </>
    );
  }
  const id = params.get("id");
  const mayReturn = role === "owner" || exchange.employeeAllowed;
  if (id !== null && mayReturn && params.get("vue") === RETURN_VIEW) {
    return (
      <ReturnPage
        key={id}
        shopId={shopId}
        refs={refs.value}
        id={id}
        onBack={() => {
          setParams({ id });
        }}
      />
    );
  }
  if (id !== null) {
    return (
      <SaleDetail
        key={id}
        shopId={shopId}
        refs={refs.value}
        id={id}
        onBack={() => {
          setParams({});
        }}
        onReturn={() => {
          setParams({ id, vue: RETURN_VIEW });
        }}
        onOpenSale={(other) => {
          setParams({ id: other });
        }}
      />
    );
  }
  return <SaleList shopId={shopId} refs={refs.value} title={title} />;
}
