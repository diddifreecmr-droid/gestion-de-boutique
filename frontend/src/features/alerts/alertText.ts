/**
 * Libellés des alertes (CDC § 20.1) et message d'échec d'une action. Un type inconnu garde son
 * code (le serveur peut en ajouter avant l'écran) ; une erreur imprévue est relancée.
 */
import { ApiError, NetworkError } from "../../core/api/errors";

const TYPE_LABELS: Readonly<Record<string, string>> = {
  low_stock: "Stock bas",
  stock_to_verify: "Stock à vérifier",
  receivable_reminder: "Rappel de créance",
  transfer_to_receive: "Déplacement à réceptionner",
  reception_gap: "Écart de réception",
  trip_expense_to_validate: "Dépense de voyage à valider",
  sale_error_reported: "Erreur signalée",
  price_request: "Demande de prix",
  breakdown: "Panne",
  truck_silent: "Camion sans nouvelle",
  document_to_renew: "Document à renouveler",
  entry_refused: "Saisie refusée",
  stock_adjustment: "Ajustement de stock",
  inventory_validated: "Inventaire validé",
};

export function alertTypeLabel(type: string): string {
  return TYPE_LABELS[type] ?? type;
}

/** « 3 alertes non lues » ; « Aucune alerte non lue ». */
export function unreadText(count: number): string {
  if (count === 0) return "Aucune alerte non lue";
  return count === 1 ? "1 alerte non lue" : `${String(count)} alertes non lues`;
}

/** Message d'un échec attendu ; toute autre erreur est relancée (fail-fast). */
export function alertActionMessage(error: unknown): string {
  if (error instanceof NetworkError) return "Connexion nécessaire : réessayez une fois en ligne.";
  if (error instanceof ApiError && error.status === 404) {
    return "Cette alerte n'existe plus pour vous : la liste est relue.";
  }
  throw error;
}
