import { useState } from "react";
import { ArrowLeft, Printer, WifiOff } from "lucide-react";
import { useGateways } from "../../core/gateways/gateways";
import type { SaleResult } from "../../core/gateways/salesContract";
import { formatDate, formatTime } from "../../shared/format";
import { Badge, Button } from "../../shared/ui";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { ErrorReports } from "./ErrorReports";
import { ReceiptPrint } from "./ReceiptPrint";
import { SaleReturnsCard } from "./returns/SaleReturnsCard";
import { ShareButton } from "./ShareButton";
import { SaleFacts } from "./SaleFacts";
import { SaleLinesCard } from "./SaleLinesCard";
import { SaleOwnerActions } from "./SaleOwnerActions";
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
  /** Ouvre « Retour ou échange » (propriétaire). */
  onReturn: () => void;
  /** Ouvre la fiche d'une autre vente (nouvelle vente d'un échange). */
  onOpenSale: (id: string) => void;
}

/**
 * Fiche d'une vente (UC-VEN-05 à 09) : lignes et détails, paiements, retours ; propriétaire :
 * coûts figés et marges, « Retour ou échange », « Annuler la vente » (sans retour) ; vendeur :
 * « Signaler une erreur » et la suite donnée. « Imprimer » ouvre la vue d'impression (le
 * serveur compte l'impression).
 */
export function SaleDetail({ shopId, refs, id, onBack, onReturn, onOpenSale }: SaleDetailProps) {
  const { sales } = useGateways();
  const [attempt, setAttempt] = useState(0);
  const loaded = useLookup(`${id}:${String(attempt)}`, () => sales.getSale(shopId, id));
  const returns = useLookup(`${id}:${String(attempt)}:retours`, () =>
    sales.listReturns(shopId, id),
  );
  const [updated, setUpdated] = useState<SaleResult | null>(null);
  const [printing, setPrinting] = useState(false);
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
  const listing = returns.status === "ready" ? returns.value : null;

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
      {listing !== null && listing.returns.length > 0 && (
        <SaleReturnsCard returns={listing.returns} refs={refs} onOpenSale={onOpenSale} />
      )}
      {returns.status === "offline" && (
        <p className="m-0 flex items-start gap-2 text-body text-text-muted">
          <WifiOff aria-hidden="true" className="size-6 shrink-0" />
          <span>Retours de la vente : connexion nécessaire.</span>
        </p>
      )}
      <ErrorReports
        shopId={shopId}
        saleId={sale.id}
        reports={sale.error_reports}
        canReport={refs.role === "seller" && sale.status === "valid"}
        onReported={(report) => {
          setUpdated({ ...sale, error_reports: [...sale.error_reports, report] });
        }}
      />
      {refs.role === "owner" && (
        <SaleOwnerActions
          shopId={shopId}
          sale={sale}
          listing={listing}
          onCancelled={setUpdated}
          onReturn={onReturn}
        />
      )}
    </>
  );
}
