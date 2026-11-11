/**
 * Ce que l'écran de vente lit du catalogue : `/profile`, `/payment-modes`, `/articles` et
 * `/stock` (specs § 6.3). Les modes de paiement sont un alias **généré** ; `CatalogArticle`
 * et `SaleSetup` ne sont pas des réponses de l'API mais leur **assemblage** par la passerelle
 * (`httpCatalog.ts` : article + stock du lieu de vente) — aucun champ n'y est inventé.
 *
 * TR-05 : un article vu par le vendeur ne porte **aucun** coût, CMP, marge ni valeur du
 * stock — ces champs n'existent pas dans ce type.
 */
import type { components } from "../api/schema.gen";
import type { DecimalString, SaleMode } from "./salesContract";

/** Point de vente (colonne `is_point_of_sale` de `GET /stock`). */
export interface SaleLocation {
  id: string;
  name: string;
}

/** Mode de paiement de la boutique (RG-T19, liste réglable). */
export type PaymentMode = components["schemas"]["PaymentModeResponse"];

export interface CatalogArticle {
  id: string;
  /** `display_name` de l'article. */
  name: string;
  sale_mode: SaleMode;
  /** Mot de l'unité (« moto ») : libellés « Couleur — moto 1 ». */
  unit_label: string;
  /** Prix de base, pré-rempli à la vente (UC-STK-03) ; `null` s'il n'est pas fixé. */
  base_price: number | null;
  /** Prix minimum actif, sinon `null` (le serveur reste juge). */
  min_price: number | null;
  /** Stock vendable au lieu de vente demandé. */
  available: DecimalString;
}

export interface ArticleSearch {
  location_id: string;
  /** Texte tapé ; vide = les plus vendus (CDC § 1.3). */
  query: string;
  limit: number;
}

/** Ce qu'il faut pour ouvrir une vente : les points de vente, le lieu habituel, les modes. */
export interface SaleSetup {
  /** Points de vente actifs, dans l'ordre d'affichage. */
  locations: SaleLocation[];
  /** Lieu habituel de l'utilisateur (`default_location_id` du profil), s'il en a un. */
  default_location_id: string | null;
  /**
   * Réglage « Accord du propriétaire sous le prix minimum » (`GET /profile`, faux par défaut) :
   * faux → un prix sous le minimum est un simple avertissement ; vrai → « Demander l'accord ».
   */
  min_price_requires_approval: boolean;
  /** Modes de paiement **actifs**, dans l'ordre d'affichage. */
  payment_modes: PaymentMode[];
}

export interface CatalogGateway {
  saleSetup(shopId: string): Promise<SaleSetup>;
  /** Résultats classés « plus vendus » d'abord (30 derniers jours), puis par nom. */
  searchArticles(shopId: string, search: ArticleSearch): Promise<{ items: CatalogArticle[] }>;
}
