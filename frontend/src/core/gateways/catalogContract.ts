/**
 * Ce que l'écran de vente lit du catalogue (specs § 6.3 : `/articles`, `/stock`, `/locations`,
 * `/payment-modes`). PROVISOIRE : alias de `schema.gen.ts` dès que ces routes existeront.
 *
 * TR-05 : un article vu par le vendeur ne porte **aucun** coût, CMP, marge ni valeur du
 * stock — ces champs n'existent pas dans ce type.
 */
import type { DecimalString, SaleMode } from "./salesContract";

export interface SaleLocation {
  id: string;
  name: string;
}

export type PaymentModeKind = "cash" | "mobile_money" | "transfer" | "cheque" | "other";

/** Mode de paiement de la boutique (RG-T19, liste réglable). */
export interface PaymentMode {
  id: string;
  label: string;
  kind: PaymentModeKind;
}

export interface CatalogArticle {
  id: string;
  name: string;
  sale_mode: SaleMode;
  /** Mot de l'unité (« moto ») : libellés « Couleur — moto 1 ». */
  unit_label: string;
  /** Prix de base, pré-rempli à la vente (UC-STK-03). */
  base_price: number;
  /** Prix minimum s'il est communiqué au rôle, sinon `null` (le serveur reste juge). */
  min_price: number | null;
  /** Stock disponible au lieu de vente demandé. */
  available: DecimalString;
}

export interface ArticleSearch {
  location_id: string;
  /** Texte tapé ; vide = les plus vendus (CDC § 1.3). */
  query: string;
  limit: number;
}

/** Ce qu'il faut pour ouvrir une vente : le lieu du vendeur et les modes de paiement. */
export interface SaleSetup {
  location: SaleLocation;
  payment_modes: PaymentMode[];
}

export interface CatalogGateway {
  saleSetup(shopId: string): Promise<SaleSetup>;
  /** Résultats classés « plus vendus » d'abord, puis par nom. */
  searchArticles(shopId: string, search: ArticleSearch): Promise<{ items: CatalogArticle[] }>;
}
