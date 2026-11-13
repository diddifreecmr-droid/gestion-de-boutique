import { ArrowLeft } from "lucide-react";
import { useGateways } from "../../../core/gateways/gateways";
import { Button, EmptyState, useToast } from "../../../shared/ui";
import { LoadingOrOffline } from "../../expenses/LoadingOrOffline";
import { locationName, type SaleRefs } from "../saleRefs";
import { useLookup } from "../useLookup";
import { deadlineText, exchangeAccess } from "./exchangeRules";
import { ReturnForm } from "./ReturnForm";

export interface ReturnPageProps {
  shopId: string;
  refs: SaleRefs;
  id: string;
  /** Retour à la fiche de la vente (après enregistrement, ou sans rien faire). */
  onBack: () => void;
}

/**
 * « Retour ou échange » d'une vente (UC-VEN-09, `?id=…&vue=retour`) : propriétaire ; l'employé
 * seulement pour un **échange** de ses ventes, si le réglage l'y autorise et dans le délai (QC-4).
 */
export function ReturnPage({ shopId, refs, id, onBack }: ReturnPageProps) {
  const seller = refs.role !== "owner";
  if (seller && !refs.exchange.employeeAllowed) {
    throw new Error("Échange par l'employé : réglage désactivé (garde de route manquante)");
  }
  const { sales } = useGateways();
  const toast = useToast();
  const loaded = useLookup(`${id}:retour`, () =>
    Promise.all([sales.getSale(shopId, id), sales.listReturns(shopId, id)]),
  );
  const heading = seller ? "Échange" : "Retour ou échange";
  if (loaded.status !== "ready") {
    return <LoadingOrOffline title={heading} status={loaded.status} />;
  }
  const [sale, listing] = loaded.value;
  const access = exchangeAccess(sale, refs, refs.exchange);
  const back = (
    <Button variant="ghost" icon={ArrowLeft} onClick={onBack}>
      Retour à la vente
    </Button>
  );
  const title = (
    <h1 className="m-0 text-title font-bold text-text">
      {heading} — <span className="font-mono">{sale.number}</span>
    </h1>
  );
  const blocked =
    sale.status !== "valid"
      ? "Cette vente est annulée : aucun retour n'est possible."
      : listing.balances.every((balance) => Number(balance.returnable) <= 0)
        ? "Tout a déjà été rendu sur cette vente."
        : seller && access.kind !== "open"
          ? (deadlineText(access) ?? "Cette vente ne peut pas être échangée par l'employé.")
          : null;
  if (blocked !== null) {
    return (
      <>
        {back}
        {title}
        <EmptyState message={blocked} />
      </>
    );
  }
  return (
    <>
      {back}
      {title}
      <ReturnForm
        shopId={shopId}
        sale={sale}
        listing={listing}
        location={{ id: sale.location_id, name: locationName(refs, sale.location_id) }}
        modes={refs.modes}
        role={refs.role}
        lineFields={refs.lineFields}
        access={access}
        onDone={(made) => {
          const text =
            made.exchange_sale_id === null
              ? `Retour enregistré — vente ${made.sale_number}`
              : `Échange enregistré — nouvelle vente ${made.exchange_sale?.number ?? ""}`.trim();
          toast.show({ tone: "success", message: text });
          onBack();
        }}
      />
    </>
  );
}
