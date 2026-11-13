import { useState } from "react";
import { Undo2, XCircle } from "lucide-react";
import { useGateways } from "../../core/gateways/gateways";
import type { SaleReturns } from "../../core/gateways/returnsContract";
import type { SaleResult } from "../../core/gateways/salesContract";
import { Button, ConfirmDialog } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "./asError";
import { HAS_RETURN } from "./returns/returnErrorMessage";
import { actionErrorMessage } from "./saleErrorMessage";

export interface SaleOwnerActionsProps {
  shopId: string;
  sale: SaleResult;
  /** Retours de la vente ; `null` tant qu'ils ne sont pas lus (aucune action proposée). */
  listing: SaleReturns | null;
  /** « Échange possible jusqu'au 20/11 » (ou délai dépassé), `null` sans délai (QC-4). */
  deadline?: string | null;
  onCancelled: (sale: SaleResult) => void;
  onReturn: () => void;
}

/**
 * Actions du propriétaire sur une vente valide : « Retour ou échange » (UC-VEN-09) tant qu'il
 * reste quelque chose à rendre, « Annuler la vente » (motif obligatoire, UC-VEN-08) tant
 * qu'aucun retour n'existe : une vente avec retour ne se modifie ni ne s'annule plus.
 */
export function SaleOwnerActions(props: SaleOwnerActionsProps) {
  const { shopId, sale, listing, deadline = null, onCancelled, onReturn } = props;
  const { sales } = useGateways();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  if (!sale.editable || listing === null) return null;
  const hasReturn = listing.returns.length > 0;
  const returnable = listing.balances.some((balance) => Number(balance.returnable) > 0);

  const cancel = async (reason: string) => {
    setConfirming(false);
    setBusy(true);
    setMessage(null);
    try {
      onCancelled(await sales.cancelSale(shopId, sale.id, reason));
    } catch (error) {
      try {
        setMessage(actionErrorMessage(error, "Annulation"));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {message !== null && <FormMessage text={message} />}
      {returnable ? (
        <>
          {deadline !== null && <p className="m-0 text-body text-text-muted">{deadline}</p>}
          <Button variant="secondary" icon={Undo2} fullWidth onClick={onReturn}>
            Retour ou échange
          </Button>
        </>
      ) : (
        <p className="m-0 text-body text-text-muted">Tout a déjà été rendu sur cette vente.</p>
      )}
      {hasReturn ? (
        <p className="m-0 text-body text-text-muted">{HAS_RETURN}</p>
      ) : (
        <Button
          variant="danger"
          icon={XCircle}
          fullWidth
          loading={busy}
          onClick={() => {
            setConfirming(true);
          }}
        >
          Annuler la vente
        </Button>
      )}
      <ConfirmDialog
        open={confirming}
        title={`Annuler la vente ${sale.number} ?`}
        confirmLabel="Annuler la vente"
        confirmIcon={XCircle}
        requireReason
        onConfirm={(reason) => {
          if (reason === null) throw new Error("Annulation sans motif : le dialogue l'exige");
          void cancel(reason);
        }}
        onCancel={() => {
          setConfirming(false);
        }}
      >
        La marchandise revient dans le stock du lieu de vente et la créance liée est annulée. La
        vente restera visible, barrée, avec la mention « Annulée ».
      </ConfirmDialog>
    </>
  );
}
