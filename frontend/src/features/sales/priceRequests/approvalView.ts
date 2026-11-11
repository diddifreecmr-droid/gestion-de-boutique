/** État de l'accord du propriétaire tel que la barre d'action l'affiche (UC-VEN-03). */
import type { PriceRequest } from "../../../core/gateways/salesContract";
import { remainingText, statusAt } from "./priceRequestText";

export type ApprovalView =
  /** Aucun prix sous le minimum : la vente se valide. */
  | { kind: "none" }
  /** Plusieurs articles sous le minimum : une demande n'en couvre qu'un. */
  | { kind: "several" }
  /** Demande à faire ; `again` : la précédente a expiré. */
  | { kind: "ask"; again: boolean }
  | { kind: "sending" }
  | { kind: "pending"; remaining: string }
  | { kind: "accepted"; remaining: string; requestId: string }
  | { kind: "refused" };

export function approvalView(
  count: number,
  sending: boolean,
  request: PriceRequest | null,
  now: number,
): ApprovalView {
  if (count === 0) return { kind: "none" };
  if (count > 1) return { kind: "several" };
  if (sending) return { kind: "sending" };
  if (request === null) return { kind: "ask", again: false };
  switch (statusAt(request, now)) {
    case "pending":
      return { kind: "pending", remaining: remainingText(request, now) };
    case "accepted":
      return { kind: "accepted", remaining: remainingText(request, now), requestId: request.id };
    case "refused":
      return { kind: "refused" };
    case "expired":
      return { kind: "ask", again: true };
  }
}
