/**
 * Message affiché quand un retour ou un échange est refusé (UC-VEN-09, T16b). Les refus de la
 * nouvelle vente d'un échange (stock, châssis, paiement…) sont dits comme sur « Nouvelle
 * vente ». Une erreur qui n'est ni une réponse de l'API ni une coupure est relancée.
 */
import { ApiError, NetworkError } from "../../../core/api/errors";
import { refundOverpayment, returnQuantityExceeded } from "../../../core/gateways/saleErrors";
import { formatMoney, formatQuantity } from "../../../shared/format";
import type { LineDraft } from "../draft";
import { saleErrorMessage } from "../saleErrorMessage";
import { MODULE_DISABLED, MODULE_DISABLED_MESSAGE } from "../../../core/profile/modules";
import { dayMonth } from "./exchangeRules";

export const RETURN_OFFLINE =
  "Connexion nécessaire : le retour n'est pas enregistré. Votre saisie est conservée ; " +
  "appuyez de nouveau sur « Enregistrer le retour » quand le réseau revient.";

export const HAS_RETURN =
  "Cette vente a un retour : elle ne se modifie ni ne s'annule plus (ses lignes servent de base aux retours).";

export const EMPLOYEE_EXCHANGE_OFF =
  "L'échange par l'employé n'est pas autorisé dans cette boutique : demandez au propriétaire.";

/** 422 `EXCHANGE_PERIOD_OVER` (`details.deadline`, `exchange_days`) : employé hors délai. */
function periodOverMessage(error: ApiError): string {
  const { deadline, exchange_days: days } = error.details;
  if (typeof deadline !== "string" || typeof days !== "number") {
    throw new Error("EXCHANGE_PERIOD_OVER : details.deadline ou exchange_days absent");
  }
  return `Délai d'échange dépassé (${String(days)} jours, jusqu'au ${dayMonth(deadline)}) : seul le propriétaire peut encore échanger cette vente.`;
}

export function returnErrorMessage(
  error: unknown,
  exchangeLines: readonly LineDraft[],
  locationName: string,
): string {
  if (error instanceof NetworkError) return RETURN_OFFLINE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "RETURN_QUANTITY_EXCEEDED": {
      const details = returnQuantityExceeded(error);
      return `Ligne ${String(details.line)} : il ne reste que ${formatQuantity(details.returnable)} à rendre. Rouvrez le retour pour relire les quantités.`;
    }
    case "OVERPAYMENT":
      if ("max" in error.details) {
        const details = refundOverpayment(error);
        return `Le remboursement dépasse ce qui peut être rendu au client : au plus ${formatMoney(details.max)}.`;
      }
      return "Le total payé dépasse le montant de la nouvelle vente.";
    case "INVALID_STATE_TRANSITION":
      return "Cette vente est annulée : aucun retour n'est possible.";
    case "VALIDATION_ERROR":
      if (error.details["field"] === "lines.chassis") {
        return "Châssis rendus à revoir : inconnus sur la ligne, en double ou déjà rendus.";
      }
      return `Retour refusé : ${error.message}.`;
    case "EXCHANGE_PERIOD_OVER":
      return periodOverMessage(error);
    case "FORBIDDEN":
      if (error.details["setting"] === "employee_exchange_allowed") return EMPLOYEE_EXCHANGE_OFF;
      return "Seul le propriétaire enregistre un retour ou un échange.";
    case MODULE_DISABLED:
      return MODULE_DISABLED_MESSAGE;
    default:
      return saleErrorMessage(error, exchangeLines, locationName);
  }
}
