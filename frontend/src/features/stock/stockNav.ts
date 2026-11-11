/**
 * Écrans de la section « Stock » : la vue est dans l'adresse (`?vue=…&id=…`), si bien que le
 * bouton retour du téléphone revient à l'écran précédent et que l'entrée « Stock » de la
 * barre du bas reste allumée. Sans paramètre : la matrice (onglet « Stock »).
 *
 * | Écran | Adresse |
 * | --- | --- |
 * | Matrice | `/s/{id}/stock` |
 * | Articles (catalogue) | `?vue=articles`, fiche `?article={id}` (module catalogue) |
 * | Historique d'un article | `?vue=mouvements&id={articleId}` |
 * | Ajustement | `?vue=ajustement` (`&id={articleId}` présélectionne l'article) |
 * | Inventaire | `?vue=inventaire` (lancement), `&id={inventoryId}` (comptage, écarts) |
 * | Valeur du stock / Stock abîmé | `?vue=valeur` / `?vue=abime` |
 */
import { useSearchParams } from "react-router";
import { shopPath } from "../../core/profile/shopProfile";
import { ARTICLES_VIEW, VIEW_PARAM } from "../catalog/catalogPaths";
import { STOCK_KEY } from "../catalog/catalogRights";

export { VIEW_PARAM };
export const ID_PARAM = "id";

export const VIEW = {
  articles: ARTICLES_VIEW,
  movements: "mouvements",
  adjustment: "ajustement",
  inventory: "inventaire",
  value: "valeur",
  damaged: "abime",
} as const;

export function stockMatrixPath(shopId: string): string {
  return shopPath(shopId, STOCK_KEY);
}

export function stockViewPath(shopId: string, view: string): string {
  return `${stockMatrixPath(shopId)}?${VIEW_PARAM}=${view}`;
}

export interface StockNav {
  matrix: () => void;
  movements: (articleId: string) => void;
  adjustment: (articleId?: string) => void;
  /** Sans identifiant : l'écran de lancement. `replace` : l'écran courant est remplacé. */
  inventory: (inventoryId?: string, replace?: boolean) => void;
  value: () => void;
  damaged: () => void;
}

export function useStockNav(): StockNav {
  const [, setParams] = useSearchParams();
  const go = (view: string, id?: string, replace = false) => {
    const params: Record<string, string> = { [VIEW_PARAM]: view };
    if (id !== undefined) params[ID_PARAM] = id;
    setParams(params, { replace });
  };
  return {
    matrix: () => {
      setParams({});
    },
    movements: (articleId) => {
      go(VIEW.movements, articleId);
    },
    adjustment: (articleId) => {
      go(VIEW.adjustment, articleId);
    },
    inventory: (inventoryId, replace = false) => {
      go(VIEW.inventory, inventoryId, replace);
    },
    value: () => {
      go(VIEW.value);
    },
    damaged: () => {
      go(VIEW.damaged);
    },
  };
}
