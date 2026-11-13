/**
 * Console plateforme (`/plateforme`) : la vue est dans l'adresse — liste sans paramètre, fiche
 * `?id=`, ouverture d'une boutique `?vue=nouvelle`. Le code provisoire du propriétaire n'est
 * **jamais** mis dans l'adresse : il n'est montré qu'une fois, en mémoire (PLT-01).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { OFFLINE_MESSAGE } from "../expenses/expenseErrors";
import { moduleRefusal } from "./moduleRefusals";
import { blockingText } from "./profileBlocking";

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

/** Types de boutique (profils du serveur, CDC § 15, § 18, § 19) : ouverture et changement de type. */
export const PROFILES = [
  { value: "motos", label: "Motos et camions" },
  { value: "apparel", label: "Prêt-à-porter" },
  { value: "textile", label: "Textile" },
] as const;

export type ProfileCode = (typeof PROFILES)[number]["value"];

/** Libellé d'un type de boutique ; un code inconnu est une rupture de contrat (fail-fast). */
export function profileLabel(code: string): string {
  const found = PROFILES.find((profile) => profile.value === code);
  if (found === undefined) throw new Error(`Type de boutique inconnu : « ${code} »`);
  return found.label;
}

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
  const refusal = moduleRefusal(error);
  if (refusal !== undefined) return refusal;
  switch (error.code) {
    case "VALIDATION_ERROR":
      return fieldsText(error);
    case "DUPLICATE":
      return "Une boutique de ce compte porte déjà ce nom.";
    case "PROFILE_CHANGE_BLOCKED":
      return blockingText(error.details["blocking"]);
    case "UNKNOWN_PROFILE":
      return "Ce type de boutique n'existe pas.";
    case "MODULE_NOT_AVAILABLE":
      return "Ce module n'existe pas pour ce type de boutique.";
    case "VERSION_CONFLICT":
      return "La boutique a été modifiée entre-temps : la fiche a été relue, vérifiez puis enregistrez de nouveau.";
    case "FORBIDDEN":
      return "Réservé à l'administrateur plateforme.";
    default:
      // 422 : règle refusée par le serveur (dépendance de modules…), message rédigé pour l'écran.
      if (error.status === 422) return `Refusé par le serveur : ${error.message}.`;
      return `L'action n'a pas abouti : ${error.message} (${error.code}).`;
  }
}

/** Refus parce que la fiche lue est périmée : il faut la relire avant de recommencer. */
export function isStale(error: unknown): boolean {
  return error instanceof ApiError && error.code === "VERSION_CONFLICT";
}
