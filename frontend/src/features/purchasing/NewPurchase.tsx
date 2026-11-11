import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type { Purchase } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { Button } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { emptyDraft } from "./draft";
import { PurchaseConfirmation } from "./PurchaseConfirmation";
import { PurchaseForm } from "./PurchaseForm";
import type { ScreenProps } from "./purchasingNav";
import { initialLocation } from "./references";
import { createBody } from "./requests";

/** « Nouvel achat » (UC-ACH-01) puis « Achat enregistré — A-000012 ». */
export function NewPurchase({ shopId, refs, nav, onSupplierSaved }: ScreenProps) {
  const { gateway, now } = usePurchasingDeps();
  const [round, setRound] = useState(0);
  const [recorded, setRecorded] = useState<Purchase | null>(null);
  /** Un identifiant par saisie : renvoyer après une coupure ne crée pas de doublon (§ 6.1). */
  const [clientId, setClientId] = useState(uuidV7);
  const today = businessDate(now());

  if (recorded !== null) {
    return (
      <PurchaseConfirmation
        purchase={recorded}
        onOpen={() => {
          nav.open(recorded.id);
        }}
        onNew={() => {
          setRecorded(null);
          setClientId(uuidV7());
          setRound((n) => n + 1);
        }}
      />
    );
  }
  return (
    <PurchaseForm
      key={round}
      shopId={shopId}
      refs={refs}
      title="Nouvel achat"
      intro={
        <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
          Retour aux achats
        </Button>
      }
      initial={emptyDraft(today, initialLocation(refs))}
      today={today}
      submitLabel="Valider l'achat"
      onSupplierSaved={onSupplierSaved}
      onSubmit={async (draft, confirm) => {
        setRecorded(await gateway.record(shopId, createBody(draft, clientId, today, confirm)));
      }}
    />
  );
}
