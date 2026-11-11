import { useEffect, useState } from "react";
import { ArrowLeft, Printer, RefreshCw } from "lucide-react";
import { useReceivablesDeps } from "../../../core/gateways/httpReceivables";
import { Button, EmptyState, Skeleton } from "../../../shared/ui";
import { useLoad } from "../../expenses/useLoad";
import { InstallmentReceiptDocument } from "./InstallmentReceiptDocument";
import "../../sales/receipt/receipt.css";

export interface InstallmentReceiptViewProps {
  shopId: string;
  installmentId: string;
  /** Retour à l'écran d'où l'on vient (confirmation ou fiche). */
  onDone: () => void;
}

/**
 * Vue d'impression du reçu de versement, chargée à la demande avec les styles du reçu de
 * vente. `GET /installments/{id}/receipt` est lu à l'ouverture et à chaque « Imprimer de
 * nouveau », puis aussitôt imprimé (`window.print()`).
 */
export default function InstallmentReceiptView(props: InstallmentReceiptViewProps) {
  const { shopId, installmentId, onDone } = props;
  const { gateway } = useReceivablesDeps();
  const [round, setRound] = useState(0);
  const key = `${installmentId}:${String(round)}`;
  const loaded = useLoad(key, () => gateway.receipt(shopId, installmentId));
  const printable = loaded.status === "ready" ? key : null;

  useEffect(() => {
    if (printable !== null) window.print();
  }, [printable]);

  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={onDone}>
        Retour
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Reçu de versement</h1>
      {loaded.status === "loading" && <Skeleton lines={6} label="Préparation du reçu…" />}
      {loaded.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour imprimer le reçu."
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
      {loaded.status === "ready" && (
        <>
          <InstallmentReceiptDocument receipt={loaded.value} />
          <Button
            variant="secondary"
            icon={Printer}
            fullWidth
            onClick={() => {
              setRound((n) => n + 1);
            }}
          >
            Imprimer de nouveau
          </Button>
        </>
      )}
    </>
  );
}
