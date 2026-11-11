/**
 * Saisie d'un ajustement ponctuel (UC-STK-08 ; backend `domain/stock/adjustment.py`) : listes
 * proposées et contrôle avant envoi. Le serveur reste juge (ADJ-02 : « Autre » exige une note).
 */
import type { AdjustmentRequest } from "../../core/gateways/stockContract";
import { isIntegral, parseQuantity } from "./quantities";

export type Direction = AdjustmentRequest["direction"];
export type Condition = AdjustmentRequest["condition"];
export type Reason = AdjustmentRequest["reason"];

export const DIRECTIONS = [
  { value: "out", label: "Sortie (−)" },
  { value: "in", label: "Entrée (+)" },
] as const satisfies readonly { value: Direction; label: string }[];

export const CONDITIONS = [
  { value: "sellable", label: "Vendable" },
  { value: "damaged", label: "Abîmé" },
] as const satisfies readonly { value: Condition; label: string }[];

const REASONS: readonly { value: Reason; label: string }[] = [
  { value: "breakage", label: "Casse" },
  { value: "theft", label: "Vol" },
  { value: "loss", label: "Perte" },
  { value: "entry_error", label: "Erreur de saisie" },
  { value: "sample_or_gift", label: "Échantillon ou cadeau" },
  { value: "supplier_return", label: "Retour au fournisseur" },
  { value: "other", label: "Autre" },
];

/** Motifs du CDC ; « Chute » (RG-X06) seulement pour un article au mètre. */
export function reasonsFor(unit: string | null) {
  if (unit === null || isIntegral(unit)) return REASONS;
  return [
    ...REASONS.slice(0, -1),
    { value: "offcut" as const, label: "Chute" },
    ...REASONS.slice(-1),
  ];
}

export const NOTE_REQUIRED = "Précisez le motif : la note est obligatoire pour « Autre »";

export interface AdjustmentDraft {
  locationId: string | null;
  articleId: string | null;
  unit: string | null;
  direction: Direction;
  condition: Condition;
  quantity: string;
  reason: Reason | null;
  note: string;
}

export type DraftErrors = Partial<
  Record<"location" | "article" | "quantity" | "reason" | "note", string>
>;

/** Erreurs de saisie (vides = prêt à l'envoi) et corps de la requête. */
export function checkDraft(
  draft: AdjustmentDraft,
  id: string,
): { errors: DraftErrors; body: AdjustmentRequest | null } {
  const errors: DraftErrors = {};
  if (draft.locationId === null) errors.location = "Choisissez le lieu";
  if (draft.articleId === null || draft.unit === null) errors.article = "Choisissez l'article";
  const parsed = draft.unit === null ? null : parseQuantity(draft.quantity, draft.unit, false);
  if (parsed !== null && !parsed.ok) errors.quantity = parsed.error;
  if (draft.reason === null) errors.reason = "Choisissez le motif";
  const note = draft.note.trim();
  if (draft.reason === "other" && note === "") errors.note = NOTE_REQUIRED;
  if (
    Object.keys(errors).length > 0 ||
    draft.locationId === null ||
    draft.articleId === null ||
    draft.reason === null ||
    parsed === null ||
    !parsed.ok
  ) {
    return { errors, body: null };
  }
  return {
    errors,
    body: {
      id,
      location_id: draft.locationId,
      article_id: draft.articleId,
      direction: draft.direction,
      quantity: parsed.value,
      condition: draft.condition,
      reason: draft.reason,
      note: note === "" ? null : note,
    },
  };
}
