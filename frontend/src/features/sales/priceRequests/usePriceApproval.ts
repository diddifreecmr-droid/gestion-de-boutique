import { useEffect, useState } from "react";
import { NetworkError } from "../../../core/api/errors";
import { uuidV7 } from "../../../core/api/uuidv7";
import { useGateways } from "../../../core/gateways/gateways";
import type { PriceRequestProblem } from "../../../core/gateways/saleErrors";
import type { PriceRequest } from "../../../core/gateways/salesContract";
import { asError } from "../asError";
import type { LineDraft } from "../draft";
import { actionErrorMessage } from "../saleErrorMessage";
import { approvalView, type ApprovalView } from "./approvalView";
import { PRICE_POLL_MS, statusAt } from "./priceRequestText";

type Entry = { status: "sending" } | { status: "known"; request: PriceRequest };

/** Clé d'une demande d'accord : un article à un prix donné (changer le prix l'invalide). */
export function approvalKey(line: LineDraft): string {
  return `${line.article.id}:${String(line.unitPrice)}`;
}

export const POLL_OFFLINE =
  "Connexion nécessaire : l'état de la demande sera relu au retour du réseau.";

/**
 * Demande d'accord du vendeur (UC-VEN-03) : création (`POST /price-requests`), puis l'état est
 * relu toutes les 10 s tant que l'écran est ouvert et que la demande attend (D19 : pas de
 * notification). Une erreur hors contrat est relancée au rendu (fail-fast).
 */
export function usePriceApproval(shopId: string, needsApproval: readonly LineDraft[]) {
  const { sales } = useGateways();
  const [entries, setEntries] = useState<Record<string, Entry>>({});
  const [now, setNow] = useState(() => Date.now());
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const [target] = needsApproval;
  const key = needsApproval.length === 1 && target !== undefined ? approvalKey(target) : null;
  const entry = key === null ? undefined : entries[key];
  const known = entry?.status === "known" ? entry.request : null;
  const set = (at: string, next: Entry | null) => {
    setEntries((current) => {
      const rest = Object.fromEntries(Object.entries(current).filter(([k]) => k !== at));
      return next === null ? rest : { ...rest, [at]: next };
    });
  };
  const failed = (error: unknown, action: string) => {
    try {
      setMessage(error instanceof NetworkError ? POLL_OFFLINE : actionErrorMessage(error, action));
    } catch (unexpected) {
      setFatal(unexpected);
    }
  };

  const refresh = async () => {
    if (key === null || known === null) return;
    setNow(Date.now());
    try {
      const request = await sales.getPriceRequest(shopId, known.id);
      setMessage(null);
      set(key, { status: "known", request });
    } catch (error) {
      failed(error, "Lecture de la demande");
    }
  };

  const ask = async () => {
    if (key === null || target === undefined || entry?.status === "sending") return;
    if (target.unitPrice === null) throw new Error("Demande d'accord sans prix");
    setMessage(null);
    set(key, { status: "sending" });
    try {
      const request = await sales.requestPriceApproval(shopId, {
        id: uuidV7(),
        article_id: target.article.id,
        requested_price: target.unitPrice,
        sale_mode: target.article.sale_mode,
      });
      setNow(Date.now());
      set(key, { status: "known", request });
    } catch (error) {
      set(key, null);
      failed(error, "Demande d'accord");
    }
  };

  /** La vente a été refusée pour cette raison : l'état affiché suit le serveur. */
  const settle = (problem: PriceRequestProblem) => {
    if (key === null || known === null) return;
    if (problem === "refused" || problem === "pending" || problem === "expired") {
      set(key, { status: "known", request: { ...known, status: problem } });
    } else if (problem !== "price_too_low") set(key, null);
  };

  const status = known === null ? null : statusAt(known, now);
  const polling = status === "pending" || status === "accepted";
  useEffect(() => {
    if (!polling) return;
    const timer = window.setInterval(() => {
      if (status === "pending") void refresh();
      else setNow(Date.now());
    }, PRICE_POLL_MS);
    return () => {
      window.clearInterval(timer);
    };
    // Relancé quand la demande suivie ou son statut changent ; `refresh` lit l'état courant.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [polling, status, known?.id, known?.version]);

  const view: ApprovalView = approvalView(
    needsApproval.length,
    entry?.status === "sending",
    known,
    now,
  );
  return { view, ask, refresh, settle, message, request: known };
}
