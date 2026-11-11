import { ArrowLeft } from "lucide-react";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { formatDate } from "../../shared/format";
import { Button, useToast } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { correctionOf } from "./correctionRule";
import { draftOf } from "./draft";
import { PurchaseForm } from "./PurchaseForm";
import type { ScreenProps } from "./purchasingNav";
import { supplierName } from "./references";
import { patchBody } from "./requests";
import { usePurchase } from "./usePurchase";

/**
 * Correction d'un achat (UC-ACH-03) : la même saisie, pré-remplie, avec un motif obligatoire ;
 * `PATCH` des seuls champs changés avec la `version` lue. Le serveur recalcule stock et CMP
 * « comme si l'achat avait été saisi juste dès le départ », et refuse si la marchandise est
 * déjà sortie (`STOCK_ALREADY_LEFT`) ou si le délai du comptable est passé.
 */
export function EditPurchase({
  shopId,
  refs,
  nav,
  id,
  onSupplierSaved,
}: ScreenProps & { id: string }) {
  const { gateway, now } = usePurchasingDeps();
  const toast = useToast();
  const loaded = usePurchase(shopId, id);
  if (loaded.status !== "ready") {
    return <LoadingOrOffline title="Corriger l'achat" status={loaded.status} />;
  }
  const { purchase, articles } = loaded.value;
  const today = businessDate(now());
  const back = (
    <Button
      variant="ghost"
      icon={ArrowLeft}
      onClick={() => {
        nav.open(id);
      }}
    >
      Retour à l'achat
    </Button>
  );
  const correction = correctionOf(purchase, refs.me.role, today);
  if (!correction.allowed) {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">Corriger l'achat</h1>
        <p className="m-0 text-body text-text">{correction.reason}</p>
        {back}
      </>
    );
  }
  const supplier = purchase.supplier_id === null ? null : supplierName(refs, purchase.supplier_id);
  return (
    <PurchaseForm
      shopId={shopId}
      refs={refs}
      title="Corriger l'achat"
      intro={
        <>
          <p className="m-0 text-body text-text-muted">
            <span className="font-mono">{purchase.number}</span> du{" "}
            {formatDate(purchase.purchase_date)}
          </p>
          {back}
        </>
      }
      initial={draftOf(purchase, supplier, articles)}
      today={today}
      submitLabel="Enregistrer la correction"
      correction={{ locationId: purchase.location_id }}
      onSupplierSaved={onSupplierSaved}
      onSubmit={async (draft, confirm, reason) => {
        const saved = await gateway.correct(
          shopId,
          id,
          patchBody(draft, purchase, reason, confirm),
        );
        toast.show({ tone: "success", message: `Achat corrigé — ${saved.number}` });
        nav.open(id);
      }}
    />
  );
}
