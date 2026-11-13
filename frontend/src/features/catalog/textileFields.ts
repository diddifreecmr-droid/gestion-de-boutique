/**
 * Fiche article **Textile** (CDC § 19, T39) : unité (mètre ou pièce), vente à la pièce,
 * longueur d'une pièce, prix au mètre et à la pièce. Reconnue aux champs servis par le profil
 * (`unit`), jamais au code du profil. Règles du serveur reprises avant l'envoi
 * (`domain/catalog/schema.py`) : vente à la pièce seulement au mètre, et longueur de la pièce
 * exigée avec elle (et seulement avec elle).
 */
import type { ProfileFieldResponse } from "../../core/gateways/catalogAdminContract";
import type { FieldDraft } from "./fieldValues";

const UNIT = "unit";
const BY_PIECE = "sold_by_piece";
const LENGTH = "piece_length_m";

/** Libellés des unités de stock servies par le profil (`choices` du champ `unit`). */
const UNIT_LABELS: Readonly<Record<string, string>> = { METER: "Mètre", PIECE: "Pièce" };

/** Le profil décrit-il des articles Textile (champ « Unité ») ? */
export function hasUnitField(fields: readonly ProfileFieldResponse[]): boolean {
  return fields.some((spec) => spec.code === UNIT);
}

/** Libellé affiché d'un choix ; une unité inconnue est une rupture de contrat (fail-fast). */
export function choiceLabel(spec: ProfileFieldResponse, choice: string): string {
  if (spec.code !== UNIT) return choice;
  const label = UNIT_LABELS[choice];
  if (label === undefined) throw new Error(`Unité de stock inconnue : « ${choice} »`);
  return label;
}

const soldByPiece = (draft: FieldDraft) => draft[BY_PIECE] === "true";

/** Champs montrés : « Vente à la pièce » au mètre seulement ; la longueur avec la vente à la pièce. */
export function shownFields(
  fields: readonly ProfileFieldResponse[],
  draft: FieldDraft,
): ProfileFieldResponse[] {
  if (!hasUnitField(fields)) return [...fields];
  return fields.filter((spec) => {
    if (spec.code === BY_PIECE) return draft[UNIT] === "METER";
    if (spec.code === LENGTH) return soldByPiece(draft);
    return true;
  });
}

/** Champs Textile tenus visibles avec les obligatoires (pas sous « Plus de détails »). */
export const TEXTILE_MAIN: ReadonlySet<string> = new Set([UNIT, BY_PIECE, LENGTH]);

/** Saisie après un changement : un champ masqué est vidé (il ne part pas au serveur). */
export function withChange(draft: FieldDraft, code: string, value: string): FieldDraft {
  const next: Record<string, string> = { ...draft, [code]: value };
  if (code === UNIT && value !== "METER" && BY_PIECE in next) next[BY_PIECE] = "";
  if (!soldByPiece(next) && LENGTH in next) next[LENGTH] = "";
  return next;
}

/** Erreur propre au Textile : la longueur manque alors que l'article se vend à la pièce. */
export function textileErrors(draft: FieldDraft): Record<string, string> {
  if (soldByPiece(draft) && (draft[LENGTH] ?? "").trim() === "") {
    return { [LENGTH]: "Longueur de la pièce : obligatoire pour la vente à la pièce" };
  }
  return {};
}

export interface PriceLabels {
  /** Libellé du prix de base (`base_price`). */
  base: string;
  /** Libellé du prix à la pièce (`base_price_piece`), `null` si l'article ne se vend pas ainsi. */
  piece: string | null;
}

/** « Prix au mètre » / « Prix à la pièce » (Textile), sinon « Prix de base ». */
export function priceLabels(unit: string | undefined, byPiece: boolean): PriceLabels {
  if (unit === "METER") return { base: "Prix au mètre", piece: byPiece ? "Prix à la pièce" : null };
  if (unit === "PIECE") return { base: "Prix à la pièce", piece: null };
  return { base: "Prix de base", piece: null };
}

/** Libellés de prix d'un article lu (valeurs par code : `unit`, `sold_by_piece`). */
export function articlePriceLabels(
  fields: readonly ProfileFieldResponse[],
  values: Readonly<Record<string, unknown>>,
): PriceLabels {
  if (!hasUnitField(fields)) return priceLabels(undefined, false);
  const unit = values[UNIT];
  return priceLabels(typeof unit === "string" ? unit : undefined, values[BY_PIECE] === true);
}

/** Libellés de prix d'une saisie (création). */
export function draftPriceLabels(
  fields: readonly ProfileFieldResponse[],
  draft: FieldDraft,
): PriceLabels {
  if (!hasUnitField(fields)) return priceLabels(undefined, false);
  return priceLabels(draft[UNIT], soldByPiece(draft));
}
