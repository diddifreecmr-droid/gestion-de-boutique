/**
 * Section « Clients » (« Plus → Clients » du propriétaire, UC-VEN-11). La vue est dans l'adresse :
 * liste `/s/{id}/clients`, fiche `?id=`, création `?vue=nouveau`, modification `?vue=modifier&id=`.
 * Le bouton retour du téléphone revient donc à l'écran précédent.
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { OFFLINE_MESSAGE } from "../expenses/expenseErrors";

export { CUSTOMERS_KEY } from "../alerts/alertLinks";

export const VIEW = { create: "nouveau", edit: "modifier" } as const;

export interface CustomerNav {
  list: () => void;
  open: (id: string) => void;
  create: () => void;
  edit: (id: string) => void;
}

export function customerNav(set: (params: Record<string, string>) => void): CustomerNav {
  return {
    list: () => {
      set({});
    },
    open: (id) => {
      set({ id });
    },
    create: () => {
      set({ vue: VIEW.create });
    },
    edit: (id) => {
      set({ vue: VIEW.edit, id });
    },
  };
}

/** Message d'un échec attendu (specs § 6.2) ; une erreur qui n'est pas de l'API est relancée. */
export function customerErrorMessage(error: unknown): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "DUPLICATE":
      return "Ce numéro de téléphone appartient déjà à un client de la boutique.";
    case "VERSION_CONFLICT":
      return "Quelqu'un a modifié ce client entre-temps : rechargez la fiche puis recommencez.";
    case "VALIDATION_ERROR":
      return `Vérifiez la saisie : ${error.message}.`;
    case "FORBIDDEN":
      return "Vous n'avez pas le droit de faire cette action.";
    default:
      return `L'action n'a pas abouti : ${error.message} (${error.code}).`;
  }
}
