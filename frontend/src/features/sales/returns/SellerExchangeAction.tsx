import { CalendarClock, Repeat } from "lucide-react";
import type { SaleReturns } from "../../../core/gateways/returnsContract";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { Button } from "../../../shared/ui";
import type { SaleRefs } from "../saleRefs";
import { deadlineText, exchangeAccess } from "./exchangeRules";

export interface SellerExchangeActionProps {
  sale: SaleResult;
  refs: SaleRefs;
  /** Retours de la vente ; `null` tant qu'ils ne sont pas lus (rien n'est proposé). */
  listing: SaleReturns | null;
  onExchange: () => void;
}

/**
 * « Échanger » pour l'employé (QC-4, EXC-L3-05) : seulement si le propriétaire l'a autorisé,
 * sur ses ventes, tant qu'il reste quelque chose à rendre ; le délai est affiché. Hors délai :
 * un message clair, sans bouton (seul le propriétaire peut encore échanger).
 */
export function SellerExchangeAction({
  sale,
  refs,
  listing,
  onExchange,
}: SellerExchangeActionProps) {
  if (refs.role !== "seller") throw new Error("SellerExchangeAction : réservé à l'employé");
  const access = exchangeAccess(sale, refs, refs.exchange);
  if (access.kind === "none" || listing === null) return null;
  if (listing.balances.every((balance) => Number(balance.returnable) <= 0)) return null;
  const text = deadlineText(access);
  return (
    <>
      {text !== null && (
        <p className="m-0 flex items-start gap-2 text-body text-text-muted">
          <CalendarClock aria-hidden="true" className="size-6 shrink-0" />
          <span>{text}</span>
        </p>
      )}
      {access.kind === "open" && (
        <Button variant="secondary" icon={Repeat} fullWidth onClick={onExchange}>
          Échanger
        </Button>
      )}
    </>
  );
}
