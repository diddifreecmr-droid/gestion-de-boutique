import { useEffect, useState } from "react";
import { ArrowLeft, Printer, RefreshCw } from "lucide-react";
import { useGateways } from "../../../core/gateways/gateways";
import { Button, EmptyState, Skeleton } from "../../../shared/ui";
import { useLookup } from "../useLookup";
import { ReceiptDocument } from "./ReceiptDocument";
import "./receipt.css";

export interface ReceiptViewProps {
  shopId: string;
  saleId: string;
  /** Retour à l'écran d'où l'on vient (confirmation ou fiche). */
  onDone: () => void;
}

/**
 * Vue d'impression (TR-18, D9), chargée à la demande avec ses styles. Chaque ouverture et
 * chaque « Imprimer de nouveau » lit `GET /sales/{id}/receipt` : le serveur compte
 * l'impression et renvoie « Duplicata » dès la 2ᵉ. Le reçu reçu est aussitôt imprimé
 * (`window.print()`), puis reste affiché à l'écran.
 */
export default function ReceiptView({ shopId, saleId, onDone }: ReceiptViewProps) {
  const { sales } = useGateways();
  const [round, setRound] = useState(0);
  const loaded = useLookup(`${saleId}:${String(round)}`, () => sales.receipt(shopId, saleId));
  const sequence = loaded.status === "ready" ? loaded.value.print_sequence : null;

  useEffect(() => {
    if (sequence !== null) window.print();
  }, [sequence]);

  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={onDone}>
        Retour
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Reçu</h1>
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
          <ReceiptDocument receipt={loaded.value} />
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
