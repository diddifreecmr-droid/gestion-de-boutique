/**
 * Mot de la pièce et règles de stock de l'écran de vente (décisions du 2026-11-15), fournis par
 * `NewSalePage` à toute la vente. Hors contexte (Motos, écrans isolés) : « pièce ».
 *
 * - `available` d'un article vaut `null` quand le stock est réservé au gérant : l'employé ne voit
 *   qu'une pastille (`stock_status`), aucun chiffre ;
 * - `sells_without_stock` : la vente n'est jamais refusée côté client (le serveur la passe et
 *   marque « Stock à vérifier ») ; sinon (Motos) la quantité reste bornée au stock du lieu.
 */
import { createContext, useContext } from "react";
import type { CatalogArticle, StockStatus } from "../../core/gateways/catalogContract";
import { pieceWords, type PieceWords } from "../../core/profile/pieceWords";

export const PieceWordsContext = createContext<PieceWords>(pieceWords("pièce"));

export function usePieceWords(): PieceWords {
  return useContext(PieceWordsContext);
}

/** Le client borne-t-il la quantité au stock du lieu (Motos) ? */
export function capped(article: CatalogArticle): boolean {
  return article.sells_without_stock !== true && article.available !== null;
}

/** Pastille de l'article : servie (employé) ; sinon déduite du chiffre (« out » à zéro). */
export function statusOf(article: CatalogArticle, hasStock: boolean): StockStatus {
  if (article.available === null) {
    if (article.stock_status === undefined) {
      throw new Error(`« ${article.name} » : ni stock ni pastille (contrat du catalogue)`);
    }
    return article.stock_status;
  }
  return hasStock ? (article.stock_status ?? "ok") : "out";
}
