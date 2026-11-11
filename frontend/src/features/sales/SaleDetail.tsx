import { useState } from "react";
import { ArrowLeft, Printer, XCircle } from "lucide-react";
import { useGateways } from "../../core/gateways/gateways";
import type { SaleResult } from "../../core/gateways/salesContract";
import { formatDate, formatTime } from "../../shared/format";
import { Badge, Button, ConfirmDialog } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { asError } from "./asError";
import { ErrorReports } from "./ErrorReports";
import { ReceiptPrint } from "./ReceiptPrint";
import { ShareButton } from "./ShareButton";
import { actionErrorMessage } from "./saleErrorMessage";
import { SaleFacts } from "./SaleFacts";
import { SaleLinesCard } from "./SaleLinesCard";
import { sellerName, type SaleRefs } from "./saleRefs";
import { useLookup } from "./useLookup";

/** « Annulée le 11/11/2026 à 10 h 00 par vous — motif : erreur de saisie » (RG-T03). */
function cancellationText(sale: SaleResult, refs: SaleRefs): string | null {
  const cancel = sale.cancellation;
  if (cancel === null) return null;
  const at = `${formatDate(cancel.cancelled_at)} à ${formatTime(cancel.cancelled_at)}`;
  return `Annulée le ${at} par ${sellerName(refs, cancel.cancelled_by)} — motif : ${cancel.reason}`;
}

export interface SaleDetailProps {
  shopId: string;
  refs: SaleRefs;
  id: string;
  onBack: () => void;
}

/**
 * Fiche d'une vente (UC-VEN-05 à 08) : lignes et détails, paiements ; propriétaire : coûts
 * figés et marges, « Annuler la vente » (motif obligatoire) ; vendeur : « Signaler une erreur »
 * et la suite donnée. « Imprimer » ouvre la vue d'impression (le serveur compte l'impression).
 */
export function SaleDetail({ shopId, refs, id, onBack }: SaleDetailProps) {
  const { sales } = useGateways();
  const [attempt, setAttempt] = useState(0);
  const loaded = useLookup(`${id}:${String(attempt)}`, () => sales.getSale(shopId, id));
  const [updated, setUpdated] = useState<SaleResult | null>(null);
  const [printing, setPrinting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  if (loaded.status !== "ready") {
    return <LoadingOrOffline title="Vente" status={loaded.status} />;
  }
  const sale = updated ?? loaded.value;
  if (printing) {
    return (
      <ReceiptPrint
        shopId={shopId}
        saleId={sale.id}
        onDone={() => {
          setPrinting(false);
          setAttempt((n) => n + 1);
        }}
      />
    );
  }
  const mention = cancellationText(sale, refs);

  const cancel = async (reason: string) => {
    setConfirming(false);
    setBusy(true);
    setMessage(null);
    try {
      setUpdated(await sales.cancelSale(shopId, sale.id, reason));
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
      <Button variant="ghost" icon={ArrowLeft} onClick={onBack}>
        Retour aux ventes
      </Button>
      <div className="flex flex-col items-start gap-2">
        <h1 className="m-0 text-title font-bold text-text">
          Vente <span className="font-mono">{sale.number}</span>
        </h1>
        {sale.status === "cancelled" && <Badge status="danger">Annulée</Badge>}
        {sale.kind === "credit" && <Badge status="credit">Crédit</Badge>}
        {mention !== null && <p className="m-0 text-body text-text">{mention}</p>}
      </div>
      <SaleLinesCard sale={sale} role={refs.role} />
      <SaleFacts sale={sale} refs={refs} />
      <div className="grid grid-cols-2 gap-4">
        <Button
          variant="secondary"
          icon={Printer}
          fullWidth
          onClick={() => {
            setPrinting(true);
          }}
        >
          Imprimer
        </Button>
        <ShareButton />
      </div>
      <ErrorReports
        shopId={shopId}
        saleId={sale.id}
        reports={sale.error_reports}
        canReport={refs.role === "seller" && sale.status === "valid"}
        onReported={(report) => {
          setUpdated({ ...sale, error_reports: [...sale.error_reports, report] });
        }}
      />
      {message !== null && <FormMessage text={message} />}
      {refs.role === "owner" && sale.editable && (
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
