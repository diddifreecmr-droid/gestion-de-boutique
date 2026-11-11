/**
 * Qui peut corriger ou annuler une dépense maintenant (UC-DEP-04), côté écran. Le serveur
 * calcule `editable` à la lecture et revérifie à chaque action ; l'écran revérifie l'heure
 * limite avec son horloge pour qu'une fiche ouverte avant minuit ne propose plus rien après.
 */
import type { Role } from "../../core/auth/me";
import type { Expense } from "../../core/gateways/expensesContract";

export const AFTER_MIDNIGHT =
  "Modifiable jusqu'à minuit le jour de la saisie — demandez au propriétaire";
export const NOT_AUTHOR = "Seul son auteur ou le propriétaire peut modifier cette dépense";
export const ALREADY_CANCELLED = "Cette dépense est annulée";

export type Correction = { allowed: true } | { allowed: false; reason: string };

export function correctionOf(expense: Expense, role: Role, userId: string, now: Date): Correction {
  if (expense.status === "cancelled") return { allowed: false, reason: ALREADY_CANCELLED };
  if (role === "owner") {
    return expense.editable ? { allowed: true } : { allowed: false, reason: NOT_AUTHOR };
  }
  if (expense.created_by !== userId) return { allowed: false, reason: NOT_AUTHOR };
  const deadline = Date.parse(expense.correction_deadline);
  if (Number.isNaN(deadline)) {
    throw new Error(`Heure limite illisible : « ${expense.correction_deadline} »`);
  }
  if (!expense.editable || now.getTime() >= deadline) {
    return { allowed: false, reason: AFTER_MIDNIGHT };
  }
  return { allowed: true };
}
