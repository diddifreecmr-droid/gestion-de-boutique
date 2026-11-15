/**
 * Fiche article **Textile** (CDC § 19, T39) : unité (mètre ou rouleau), vente au rouleau,
 * longueur du rouleau, prix au mètre et au rouleau. Reconnue aux champs servis par le profil
 * (`unit`), jamais au code du profil. Le mot « rouleau » vient du profil (`piece_label`,
 * 2026-11-15) : `words`. Règles du serveur reprises avant l'envoi (`domain/catalog/schema.py`) :
 * vente au rouleau seulement au mètre, et longueur du rouleau exigée avec elle.
 */
import type { ProfileFieldResponse } from "../../core/gateways/catalogAdminContract";
import { pieceWords, type PieceWords } from "../../core/profile/pieceWords";
import type { FieldDraft } from "./fieldValues";

const UNIT = "unit";
const BY_PIECE = "sold_by_piece";
const LENGTH = "piece_length_m";
const PIECE = pieceWords("pièce");

/** Le profil décrit-il des articles Textile (champ « Unité ») ? */
export function hasUnitField(fields: readonly ProfileFieldResponse[]): boolean {
  return fields.some((spec) => spec.code === UNIT);
}

/** Libellé affiché d'un choix ; une unité inconnue est une rupture de contrat (fail-fast). */
export function choiceLabel(
  spec: ProfileFieldResponse,
  choice: string,
  words: PieceWords = PIECE,
): string {
  if (spec.code !== UNIT) return choice;
  if (choice === "METER") return "Mètre";
  if (choice === "PIECE") return words.title;
  throw new Error(`Unité de stock inconnue : « ${choice} »`);
}

const soldByPiece = (draft: FieldDraft) => draft[BY_PIECE] === "true";

/** Champs montrés : « Vente au rouleau » au mètre seulement ; la longueur avec elle. */
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

/** Erreur propre au Textile : la longueur manque alors que l'article se vend au rouleau. */
export function textileErrors(draft: FieldDraft, words: PieceWords = PIECE): Record<string, string> {
  if (soldByPiece(draft) && (draft[LENGTH] ?? "").trim() === "") {
    return { [LENGTH]: `Longueur ${words.of} : obligatoire pour la vente ${words.per}` };
  }
  return {};
}

export interface PriceLabels {
  /** Libellé du prix de base (`base_price`). */
  base: string;
  /** Libellé du prix au rouleau (`base_price_piece`), `null` s'il ne se vend pas ainsi. */
  piece: string | null;
  /** Libellé du minimum au rouleau (`min_price_piece`), avec `piece`. */
  pieceMinimum: string | null;
}

/** « Prix au mètre » / « Prix au rouleau » (Textile), sinon « Prix de base ». */
export function priceLabels(
  unit: string | undefined,
  byPiece: boolean,
  words: PieceWords = PIECE,
): PriceLabels {
  const perPiece = `Prix ${words.per}`;
  if (unit === "METER") {
    return byPiece
      ? { base: "Prix au mètre", piece: perPiece, pieceMinimum: `Minimum ${words.per}` }
      : { base: "Prix au mètre", piece: null, pieceMinimum: null };
  }
  if (unit === "PIECE") return { base: perPiece, piece: null, pieceMinimum: null };
  return { base: "Prix de base", piece: null, pieceMinimum: null };
}

/** Libellés de prix d'un article lu (valeurs par code : `unit`, `sold_by_piece`). */
export function articlePriceLabels(
  fields: readonly ProfileFieldResponse[],
  values: Readonly<Record<string, unknown>>,
  words: PieceWords = PIECE,
): PriceLabels {
  if (!hasUnitField(fields)) return priceLabels(undefined, false, words);
  const unit = values[UNIT];
  const byPiece = values[BY_PIECE] === true;
  return priceLabels(typeof unit === "string" ? unit : undefined, byPiece, words);
}

/** Libellés de prix d'une saisie (création). */
export function draftPriceLabels(
  fields: readonly ProfileFieldResponse[],
  draft: FieldDraft,
  words: PieceWords = PIECE,
): PriceLabels {
  if (!hasUnitField(fields)) return priceLabels(undefined, false, words);
  return priceLabels(draft[UNIT], soldByPiece(draft), words);
}
