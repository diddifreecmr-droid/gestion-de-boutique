import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useSearchParams } from "react-router";
import { useGateways } from "../../core/gateways/gateways";
import { useSignedIn } from "../../core/services/servicesContext";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { ReturnPage } from "./returns/ReturnPage";
import { SaleDetail } from "./SaleDetail";
import { SaleList } from "./SaleList";
import { loadSaleRefs } from "./saleRefs";
import type { SaleRole } from "./salesNav";
import { useLookup } from "./useLookup";

/** Vue « Retour ou échange » d'une vente (`?id=…&vue=retour`, propriétaire). */
export const RETURN_VIEW = "retour";

/** Section des ventes (UC-VEN-05 à 08) : liste du jour, fiche `?id=`, reçu, annulation. */
export function SalesPage({
  shopId,
  role,
  title,
}: {
  shopId: string;
  role: SaleRole;
  title: string;
}) {
  const me = useSignedIn();
  const gateways = useGateways();
  const [params, setParams] = useSearchParams();
  const [round, setRound] = useState(0);
  const refs = useLookup(`${shopId}:${String(round)}`, () =>
    loadSaleRefs(gateways, shopId, { role, userId: me.userId }),
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
  if (id !== null && role === "owner" && params.get("vue") === RETURN_VIEW) {
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
