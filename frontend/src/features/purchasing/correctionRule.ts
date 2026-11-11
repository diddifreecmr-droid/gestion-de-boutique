/**
 * Ce que l'utilisateur peut encore faire d'un achat (UC-ACH-03, 04, 06), côté écran. Le serveur
 * calcule `editable` / `cancellable` à la lecture et revérifie à chaque action ; l'écran
 * revérifie le délai du comptable avec son horloge, en jour métier de Douala : une fiche ouverte
 * le dernier jour ne propose plus « Corriger » le lendemain.
 */
import type { Purchase } from "../../core/gateways/purchasingContract";
import { formatDate } from "../../shared/format";
import type { PurchaseRole } from "./purchasingNav";

export const CANCELLED = "Cet achat est annulé";
export const FULLY_PAID = "Cet achat est entièrement payé";

export type Allowed = { allowed: true } | { allowed: false; reason: string };

/** « Corrigeable par le comptable jusqu'au 18/11/2026 — demandez au propriétaire ». */
export function windowClosedText(lastDay: string): string {
  return `Corrigeable par le comptable jusqu'au ${formatDate(lastDay)} — demandez au propriétaire`;
}

export function correctionOf(purchase: Purchase, role: PurchaseRole, today: string): Allowed {
  if (purchase.status === "cancelled") return { allowed: false, reason: CANCELLED };
  if (role === "accountant" && (today > purchase.last_correction_day || !purchase.editable)) {
    return { allowed: false, reason: windowClosedText(purchase.last_correction_day) };
  }
  if (!purchase.editable) {
    throw new Error(`Achat ${purchase.number} valide mais non corrigeable par le propriétaire`);
  }
  return { allowed: true };
}

export function paymentOf(purchase: Purchase): Allowed {
  if (purchase.status === "cancelled") return { allowed: false, reason: CANCELLED };
  if (purchase.paid >= purchase.total) return { allowed: false, reason: FULLY_PAID };
  return { allowed: true };
}

/** Reste à payer au fournisseur (jamais négatif : le serveur refuse le trop-payé). */
export function remainingOf(purchase: Purchase): number {
  const remaining = purchase.total - purchase.paid;
  if (remaining < 0) throw new Error(`Achat ${purchase.number} payé au-delà de son total`);
  return remaining;
}
