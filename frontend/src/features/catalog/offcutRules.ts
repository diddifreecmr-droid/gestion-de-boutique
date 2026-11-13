/**
 * « Déclarer une chute » (RG-X06, UC-TEX-03, design-system § 7.5) : ajustement en **sortie**,
 * motif « Chute », longueur au dixième (QC-3) au plus le stock vendable du lieu, note et photo
 * facultatives. Le serveur reste juge (employé : 403 ; stock : 422 STOCK_INSUFFICIENT).
 */
import type { AdjustmentRequest, StockMatrix } from "../../core/gateways/stockContract";
import { metersText, parseLength, tenthsValue, toTenths } from "../sales/textile";

export interface OffcutPlace {
  id: string;
  name: string;
  /** Stock vendable du lieu, en dixièmes de mètre. */
  tenths: number;
}

/** Lieux où l'article a du stock vendable (une seule « Boutique » au Lot 3, QC-5). */
export function offcutPlaces(matrix: StockMatrix, articleId: string): OffcutPlace[] {
  const row = matrix.items.find((item) => item.article_id === articleId);
  if (row === undefined) return [];
  return matrix.locations
    .map((place) => {
      const cell = row.cells.find((one) => one.location_id === place.location_id);
      if (cell === undefined) throw new Error(`Stock : colonne « ${place.name} » absente`);
      return { id: place.location_id, name: place.name, tenths: toTenths(cell.sellable) };
    })
    .filter((place) => place.tenths > 0);
}

export interface OffcutDraft {
  length: string;
  note: string;
  photoId: string | null;
}

export interface OffcutCheck {
  error: string | undefined;
  body: AdjustmentRequest | null;
  /** Longueur lue (dixièmes), pour la confirmation et le message de réussite. */
  tenths: number | null;
}

export function checkOffcut(
  draft: OffcutDraft,
  place: OffcutPlace,
  articleId: string,
  id: string,
): OffcutCheck {
  const length = parseLength(draft.length);
  if (!length.ok) return { error: length.error, body: null, tenths: null };
  if (length.tenths > place.tenths) {
    const error = `La chute dépasse le stock : ${metersText(place.tenths)} à ${place.name}`;
    return { error, body: null, tenths: null };
  }
  const note = draft.note.trim();
  return {
    error: undefined,
    tenths: length.tenths,
    body: {
      id,
      location_id: place.id,
      article_id: articleId,
      direction: "out",
      quantity: tenthsValue(length.tenths),
      condition: "sellable",
      reason: "offcut",
      note: note === "" ? null : note,
      photo_id: draft.photoId,
    },
  };
}
