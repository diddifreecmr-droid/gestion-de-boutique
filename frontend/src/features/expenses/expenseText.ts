/** Textes communs à la liste et à la fiche d'une dépense (formats de `shared/format`). */
import type { Expense } from "../../core/gateways/expensesContract";
import { formatDate, formatTime } from "../../shared/format";
import { cancellerName, type References } from "./references";

/** RG-T03 : « Annulée le 11/11/2026 à 14 h 32 par Awa Bello — motif : doublon ». */
export function cancellationText(refs: References, expense: Expense): string | null {
  const cancel = expense.cancellation;
  if (expense.status !== "cancelled") return null;
  if (cancel === null) throw new Error(`Dépense ${expense.number} annulée sans annulation`);
  const when = `${formatDate(cancel.cancelled_at)} à ${formatTime(cancel.cancelled_at)}`;
  return `Annulée le ${when} par ${cancellerName(refs, cancel.cancelled_by)} — motif : ${cancel.reason}`;
}
