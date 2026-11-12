/**
 * Console plateforme (`/plateforme`) : la vue est dans l'adresse — liste sans paramètre, fiche
 * `?id=`, ouverture d'une boutique `?vue=nouvelle`. Le code provisoire du propriétaire n'est
 * **jamais** mis dans l'adresse : il n'est montré qu'une fois, en mémoire (PLT-01).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { OFFLINE_MESSAGE } from "../expenses/expenseErrors";

export const VIEW = { create: "nouvelle" } as const;

export interface PlatformNav {
  list: () => void;
  open: (shopId: string) => void;
  create: () => void;
}

export function platformNav(set: (params: Record<string, string>) => void): PlatformNav {
  return {
    list: () => {
      set({});
    },
    open: (shopId) => {
      set({ id: shopId });
    },
    create: () => {
      set({ vue: VIEW.create });
    },
  };
}

/** Profils proposés à l'ouverture : seul « Motos » est livré au Lot 1 (Prêt-à-porter, Textile : Lot 3). */
export const PROFILES = [{ value: "motos", label: "Motos et camions" }] as const;

export const STATUS_LABELS: Readonly<Record<string, string>> = {
  active: "Ouverte",
  closed: "Fermée",
};

function fieldsText(error: ApiError): string {
  const fields = error.details["fields"];
  if (!Array.isArray(fields) || fields.length === 0) return `${error.message}.`;
  return `Vérifiez la saisie (${String(fields.length)} champ(s) à corriger) : ${error.message}.`;
}

/** Message d'un échec attendu (specs § 6.2) ; une erreur qui n'est pas de l'API est relancée. */
export function platformErrorMessage(error: unknown): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "VALIDATION_ERROR":
      return fieldsText(error);
    case "DUPLICATE":
      return "Une boutique de ce compte porte déjà ce nom.";
    case "UNKNOWN_PROFILE":
      return "Ce type de boutique n'existe pas.";
    case "MODULE_NOT_AVAILABLE":
      return "Ce module n'existe pas pour ce type de boutique.";
    case "FORBIDDEN":
      return "Réservé à l'administrateur plateforme.";
    default:
      return `L'action n'a pas abouti : ${error.message} (${error.code}).`;
  }
}
