import { useState } from "react";
import { BadgePercent, RefreshCw, WifiOff } from "lucide-react";
import { useGateways } from "../../../core/gateways/gateways";
import type { PriceDecision, PriceRequest } from "../../../core/gateways/salesContract";
import { Button, EmptyState, Skeleton, useToast } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { asError } from "../asError";
import { actionErrorMessage } from "../saleErrorMessage";
import { decisionErrorMessage } from "./decisionError";
import { PriceRequestRow } from "./PriceRequestRow";
import { usePendingRequests } from "./usePendingRequests";

export const PRICE_REQUESTS_TITLE = "Demandes de prix";

/**
 * Demandes de prix sous le minimum en attente (UC-VEN-03 ; accueil du propriétaire,
 * UC-TDB-01 point 6). La liste est relue toutes les 10 s ; une décision la met à jour aussitôt.
 */
export function PriceRequestsPage({ shopId }: { shopId: string }) {
  const { sales } = useGateways();
  const toast = useToast();
  const { state, drop, reload } = usePendingRequests(shopId, true);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const title = <h1 className="m-0 text-title font-bold text-text">{PRICE_REQUESTS_TITLE}</h1>;
  if (state.status !== "ready") {
    return (
      <>
        {title}
        {state.status === "loading" ? (
          <Skeleton lines={4} label="Chargement des demandes…" />
        ) : (
          <EmptyState icon={WifiOff} message="Connexion nécessaire pour afficher les demandes." />
        )}
      </>
    );
  }

  const decide = async (request: PriceRequest, decision: PriceDecision) => {
    setBusy(request.id);
    setMessage(null);
    try {
      await sales.decidePriceRequest(shopId, request.id, decision, request.version);
      drop(request.id);
      const verdict = decision === "accept" ? "acceptée" : "refusée";
      toast.show({ tone: "success", message: `Demande ${verdict} — ${request.article_name}` });
    } catch (error) {
      try {
        const known = decisionErrorMessage(error);
        setMessage(known ?? actionErrorMessage(error, "Décision"));
        if (known !== null) reload();
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(null);
    }
  };

  const name = (id: string) =>
    state.members.find((m) => m.user_id === id)?.name ?? "Vendeur inconnu";
  return (
    <>
      {title}
      {state.offline && (
        <p className="m-0 text-body text-text-muted">
          Connexion nécessaire : la liste sera relue au retour du réseau.
        </p>
      )}
      {message !== null && <FormMessage text={message} />}
      {state.items.length === 0 ? (
        <EmptyState icon={BadgePercent} message="Aucune demande de prix en attente." />
      ) : (
        <ul
          aria-label="Demandes en attente"
          className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card"
        >
          {state.items.map((request) => (
            <PriceRequestRow
              key={request.id}
              request={request}
              sellerName={name(request.seller_id)}
              now={state.at}
              busy={busy === request.id}
              onDecide={(decision) => void decide(request, decision)}
            />
          ))}
        </ul>
      )}
      <Button variant="secondary" icon={RefreshCw} fullWidth onClick={reload}>
        Actualiser
      </Button>
    </>
  );
}
