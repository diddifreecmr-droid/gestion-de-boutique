/**
 * Textes des demandes d'accord de prix (UC-VEN-03) : temps restant, statut effectif, et le
 * message de chaque raison de `PRICE_BELOW_MINIMUM.details.price_request` (T16b).
 */
import type { PriceRequestProblem } from "../../../core/gateways/saleErrors";
import {
  priceRequestStatus,
  type PriceRequest,
  type PriceRequestStatus,
} from "../../../core/gateways/salesContract";
import { formatMoney } from "../../../shared/format";

/** Rafraîchissement de l'état tant que l'écran est ouvert (pas de notification push, D19). */
export const PRICE_POLL_MS = 10_000;

/** Statut à l'heure de l'appareil : une demande ouverte échue est « expirée ». */
export function statusAt(request: PriceRequest, now: number): PriceRequestStatus {
  const status = priceRequestStatus(request);
  const open = status === "pending" || (status === "accepted" && request.sale_id === null);
  return open && now >= Date.parse(request.expires_at) ? "expired" : status;
}

/** « 29 min », « moins d'une minute ». */
export function remainingText(request: PriceRequest, now: number): string {
  const minutes = Math.floor((Date.parse(request.expires_at) - now) / 60_000);
  return minutes < 1 ? "moins d'une minute" : `${String(minutes)} min`;
}

export const PENDING_TEXT = "En attente de l'accord du propriétaire";
export const REFUSED_TEXT = "Le propriétaire a refusé ce prix : changez le prix.";
export const EXPIRED_TEXT =
  "La demande a expiré sans réponse (30 minutes) : demandez de nouveau ou changez le prix.";
export const ONE_ARTICLE_TEXT =
  "Une demande d'accord couvre un seul article : remontez les autres prix au minimum ou faites une vente séparée.";

/** Message du refus de la vente quand la demande jointe ne couvre pas la ligne. */
export function problemMessage(problem: PriceRequestProblem, request: PriceRequest | null): string {
  switch (problem) {
    case "not_found":
      return "Demande d'accord introuvable : demandez de nouveau l'accord du propriétaire.";
    case "other_seller":
      return "Cette demande d'accord a été faite par un autre vendeur : demandez votre propre accord.";
    case "other_article":
      return "L'accord du propriétaire porte sur un autre article : une demande ne couvre qu'un article.";
    case "pending":
      return "Le propriétaire n'a pas encore répondu : attendez son accord ou changez le prix.";
    case "refused":
      return REFUSED_TEXT;
    case "expired":
      return "L'accord a expiré (30 minutes) : demandez de nouveau ou changez le prix.";
    case "used":
      return "Cet accord a déjà servi pour une autre vente : demandez un nouvel accord.";
    case "price_too_low":
      return request === null
        ? "Le prix est inférieur au prix accordé : remontez-le."
        : `Le prix est inférieur au prix accordé : il doit être d'au moins ${formatMoney(request.requested_price)}.`;
  }
}
