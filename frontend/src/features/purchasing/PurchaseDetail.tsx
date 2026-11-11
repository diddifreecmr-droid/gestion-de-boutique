import { useState } from "react";
import { ArrowLeft, Banknote, Pencil, XCircle } from "lucide-react";
import type { Purchase } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { formatDate, formatTime } from "../../shared/format";
import { Button, ConfirmDialog } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { asError } from "../expenses/useLoad";
import { correctionOf, paymentOf } from "./correctionRule";
import { PaymentBadge } from "./PaymentBadge";
import { PaymentsCard } from "./PaymentsCard";
import { purchaseErrorMessage } from "./purchaseErrors";
import { PurchaseFacts } from "./PurchaseFacts";
import type { ScreenProps } from "./purchasingNav";
import { usePurchase } from "./usePurchase";

/** « Annulé le 12/11/2026 à 9 h 05 par le propriétaire — motif : erreur de saisie ». */
function cancellationText(purchase: Purchase, myId: string): string | null {
  const cancel = purchase.cancellation;
  if (cancel === null) return null;
  const by = cancel.cancelled_by === myId ? "vous" : "le propriétaire";
  const at = `${formatDate(cancel.cancelled_at)} à ${formatTime(cancel.cancelled_at)}`;
  return `Annulé le ${at} par ${by} — motif : ${cancel.reason}`;
}

/** Fiche d'un achat (UC-ACH-03 à 06) : lignes et coûts, paiements, corriger, annuler, payer. */
export function PurchaseDetail({ shopId, refs, nav, id }: ScreenProps & { id: string }) {
  const { gateway, now } = usePurchasingDeps();
  const loaded = usePurchase(shopId, id);
  const [updated, setUpdated] = useState<Purchase | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  if (loaded.status !== "ready") return <LoadingOrOffline title="Achat" status={loaded.status} />;

  const purchase = updated ?? loaded.value.purchase;
  const correction = correctionOf(purchase, refs.me.role, businessDate(now()));
  const payment = paymentOf(purchase);
  const mention = cancellationText(purchase, refs.me.userId);

  const cancel = async (reason: string) => {
    setConfirming(false);
    setBusy(true);
    setMessage(null);
    try {
      setUpdated(await gateway.cancel(shopId, id, reason));
    } catch (error) {
      try {
        setMessage(purchaseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux achats
      </Button>
      <div className="flex flex-col items-start gap-2">
        <h1 className="m-0 text-title font-bold text-text">
          Achat <span className="font-mono">{purchase.number}</span>
        </h1>
        <PaymentBadge purchase={purchase} />
        {mention !== null && <p className="m-0 text-body text-text">{mention}</p>}
      </div>
      <PurchaseFacts refs={refs} loaded={{ ...loaded.value, purchase }} />
      <PaymentsCard refs={refs} purchase={purchase} />
      {message !== null && <FormMessage text={message} />}
      {purchase.status === "valid" && (
        <div className="flex flex-col gap-4">
          <Button
            variant="secondary"
            icon={Banknote}
            fullWidth
            onClick={() => {
              nav.payment(id);
            }}
            {...(payment.allowed ? {} : { disabledReason: payment.reason })}
          >
            Noter un paiement
          </Button>
          <Button
            variant="secondary"
            icon={Pencil}
            fullWidth
            onClick={() => {
              nav.edit(id);
            }}
            {...(correction.allowed ? {} : { disabledReason: correction.reason })}
          >
            Corriger l'achat
          </Button>
          {purchase.cancellable && (
            <Button
              variant="danger"
              icon={XCircle}
              fullWidth
              loading={busy}
              onClick={() => {
                setConfirming(true);
              }}
            >
              Annuler l'achat
            </Button>
          )}
        </div>
      )}
      <ConfirmDialog
        open={confirming}
        title={`Annuler l'achat ${purchase.number} ?`}
        confirmLabel="Annuler l'achat"
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
        Le stock reçu sera retiré du lieu et le coût moyen recalculé. L'achat restera visible,
        barré, et ne comptera plus dans aucun total.
      </ConfirmDialog>
    </>
  );
}
