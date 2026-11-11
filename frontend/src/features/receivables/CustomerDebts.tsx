import { useState, type ReactNode } from "react";
import { Search } from "lucide-react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { CustomerSummary, Receivable } from "../../core/gateways/receivablesContract";
import { formatMoney } from "../../shared/format";
import { Button, ChoiceChips, EmptyState, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { debtsOf, originText } from "./receivableRules";

export interface CustomerDebtsProps {
  shopId: string;
  customer: CustomerSummary;
  onChangeCustomer: () => void;
  children: (receivable: Receivable) => ReactNode;
}

/** Choix de la créance à payer : par défaut la plus ancienne ; l'utilisateur peut en choisir une autre. */
export function CustomerDebts({
  shopId,
  customer,
  onChangeCustomer,
  children,
}: CustomerDebtsProps) {
  const { gateway } = useReceivablesDeps();
  const listing = useLoad(customer.id, () => gateway.list(shopId, {}));
  const [chosen, setChosen] = useState<string | null>(null);
  const change = (
    <Button variant="ghost" icon={Search} onClick={onChangeCustomer}>
      Changer de client
    </Button>
  );
  if (listing.status === "loading") return <Skeleton lines={3} label="Recherche des créances…" />;
  if (listing.status === "offline") {
    return <EmptyState message="Connexion nécessaire pour lire les créances du client." />;
  }
  const debts = debtsOf(listing.value.items, customer.id);
  const [oldest] = debts;
  if (oldest === undefined) {
    return <EmptyState message={`${customer.name} n'a aucune créance à payer.`} action={change} />;
  }
  const target = debts.find((item) => item.id === chosen) ?? oldest;
  return (
    <>
      <p className="m-0 text-lead break-words text-text">
        {customer.name} — {customer.phone}
      </p>
      {change}
      {debts.length > 1 && (
        <ChoiceChips
          label="Créance à payer"
          options={debts.map((item, index) => ({
            value: item.id,
            label: `${index === 0 ? "La plus ancienne : " : ""}${originText(item)} — reste ${formatMoney(item.remaining)}`,
          }))}
          value={target.id}
          onChange={setChosen}
        />
      )}
      {children(target)}
    </>
  );
}
