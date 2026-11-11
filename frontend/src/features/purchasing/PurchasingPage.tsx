import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useSearchParams } from "react-router";
import type { Supplier } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { useSignedIn } from "../../core/services/servicesContext";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { EditPurchase } from "./EditPurchase";
import { NewPurchase } from "./NewPurchase";
import { PaymentPage } from "./PaymentPage";
import { PurchaseDetail } from "./PurchaseDetail";
import { PurchaseList } from "./PurchaseList";
import { purchaseNav, VIEW, type PurchaseRole, type ScreenProps } from "./purchasingNav";
import { loadReferences, withSupplier } from "./references";
import { SupplierDetail } from "./SupplierDetail";
import { SupplierEdit, SupplierNew } from "./SupplierEdit";
import { SupplierList } from "./SupplierList";

/**
 * Section « Achats » (UC-ACH-01 à 06) : liste, nouvel achat, fiche, correction, paiement,
 * fournisseurs. Les référentiels sont lus une fois ; un fournisseur créé ou modifié y est
 * ajouté aussitôt (création rapide pendant la saisie).
 */
export function PurchasingPage({ shopId, role }: { shopId: string; role: PurchaseRole }) {
  const me = useSignedIn();
  const { gateway } = usePurchasingDeps();
  const [params, setParams] = useSearchParams();
  const [round, setRound] = useState(0);
  const [saved, setSaved] = useState<readonly Supplier[]>([]);
  const loaded = useLoad(`${shopId}:${String(round)}`, () =>
    loadReferences(gateway, shopId, { userId: me.userId, role }),
  );

  if (loaded.status !== "ready") {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">Achats</h1>
        {loaded.status === "loading" ? (
          <Skeleton lines={4} label="Chargement des achats…" />
        ) : (
          <EmptyState
            message="Connexion nécessaire pour ouvrir les achats."
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

  const common: ScreenProps = {
    shopId,
    refs: saved.reduce(withSupplier, loaded.value),
    nav: purchaseNav(setParams),
    onSupplierSaved: (supplier) => {
      setSaved((current) => [...current, supplier]);
    },
  };
  const view = params.get("vue");
  const id = params.get("id");
  if (view === VIEW.create) return <NewPurchase {...common} />;
  if (view === VIEW.suppliers) return <SupplierList {...common} />;
  if (view === VIEW.newSupplier) return <SupplierNew {...common} />;
  if (id !== null) {
    switch (view) {
      case VIEW.detail:
        return <PurchaseDetail key={id} {...common} id={id} />;
      case VIEW.edit:
        return <EditPurchase key={id} {...common} id={id} />;
      case VIEW.payment:
        return <PaymentPage key={id} {...common} id={id} />;
      case VIEW.supplier:
        return <SupplierDetail key={id} {...common} id={id} />;
      case VIEW.editSupplier:
        return <SupplierEdit key={id} {...common} id={id} />;
    }
  }
  return <PurchaseList {...common} />;
}
