/** Prix saisis à la création (propriétaire) ; `piece` seulement pour un article vendu à la pièce. */
export interface CreatePrices {
  base: number | null;
  minimum: number | null;
  piece: number | null;
  minimumPiece: number | null;
}

export const NO_PRICES: CreatePrices = {
  base: null,
  minimum: null,
  piece: null,
  minimumPiece: null,
};
