import { useEffect, useState } from "react";
import { NetworkError } from "../../../core/api/errors";
import { useGateways } from "../../../core/gateways/gateways";
import type { PriceRequest, SaleMember } from "../../../core/gateways/salesContract";
import { asError } from "../asError";
import { PRICE_POLL_MS } from "./priceRequestText";

export type PendingState =
  | { status: "loading" }
  | { status: "offline" }
  | {
      status: "ready";
      items: PriceRequest[];
      members: SaleMember[];
      offline: boolean;
      /** Heure de la dernière lecture (temps restant). */
      at: number;
    };

/**
 * Demandes en attente vues par le propriétaire (`GET /price-requests`), relues toutes les 10 s
 * tant que l'écran est ouvert (D19). Coupure : la dernière liste reste, signalée hors ligne.
 * Toute autre erreur est relancée au rendu (fail-fast).
 */
export function usePendingRequests(shopId: string, withMembers: boolean) {
  const { sales } = useGateways();
  const [state, setState] = useState<PendingState>({ status: "loading" });
  const [fatal, setFatal] = useState<unknown>(null);
  const [round, setRound] = useState(0);
  if (fatal !== null) throw asError(fatal);

  useEffect(() => {
    let current = true;
    const load = async () => {
      try {
        const [items, members] = await Promise.all([
          sales.listPriceRequests(shopId),
          withMembers ? sales.members(shopId) : Promise.resolve([]),
        ]);
        if (current) setState({ status: "ready", items, members, offline: false, at: Date.now() });
      } catch (error) {
        if (!current) return;
        if (!(error instanceof NetworkError)) setFatal(error);
        else
          setState((s) => (s.status === "ready" ? { ...s, offline: true } : { status: "offline" }));
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), PRICE_POLL_MS);
    return () => {
      current = false;
      window.clearInterval(timer);
    };
  }, [sales, shopId, withMembers, round]);

  /** Retire une demande décidée sans attendre la prochaine relecture. */
  const drop = (id: string) => {
    setState((s) =>
      s.status === "ready" ? { ...s, items: s.items.filter((r) => r.id !== id) } : s,
    );
  };
  const reload = () => {
    setRound((n) => n + 1);
  };
  return { state, drop, reload };
}
