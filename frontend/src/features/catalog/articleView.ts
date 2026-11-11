/**
 * Article **vu par un rôle** (TR-05, RG-D02, CDC § 4.2). L'écran ne lit jamais
 * `ArticleResponse` directement : ce module recopie seulement ce que le rôle a le droit de
 * voir, même si le serveur en envoyait plus (défense en profondeur).
 *
 * | Vue | Prix de vente | Coûts (dernier coût, CMP) | Historique des prix |
 * | --- | --- | --- | --- |
 * | `owner` | oui | oui | oui (fiche) |
 * | `accountant` | **non** | oui | non |
 * | `seller` | oui | **le type n'a pas de champ de coût** | non |
 */
import type { Role } from "../../core/auth/me";
import type {
  ArticleResponse,
  FieldValue,
  PriceHistoryResponse,
} from "../../core/gateways/catalogAdminContract";

export interface ArticleCore {
  id: string;
  version: number;
  archived: boolean;
  name: string;
  /** Valeur de chaque champ du profil, par code (`brand`, `model`, `engine_cc`…). */
  values: Readonly<Record<string, FieldValue>>;
  alertThreshold: string | null;
  effectiveThreshold: string;
  notes: string | null;
}

export interface SellingPrices {
  basePrice: number | null;
  minPrice: number | null;
  /** Réglage « prix minimum » actif dans la boutique. */
  minPriceActive: boolean;
  /** Prix à la pièce (Textile) : conservés tels quels lors d'un `PUT /prices`. */
  basePricePiece: number | null;
  minPricePiece: number | null;
}

/** `null` = « non calculable » (aucun achat encore). */
export interface Costs {
  lastCost: number | null;
  wac: number | null;
}

export interface OwnerArticle extends ArticleCore {
  kind: "owner";
  prices: SellingPrices;
  costs: Costs;
  /** Présent sur la fiche, `null` dans la liste. */
  history: readonly PriceHistoryResponse[] | null;
}

export interface AccountantArticle extends ArticleCore {
  kind: "accountant";
  costs: Costs;
}

export interface SellerArticle extends ArticleCore {
  kind: "seller";
  prices: SellingPrices;
}

export type ArticleView = OwnerArticle | AccountantArticle | SellerArticle;

function contractError(field: string, role: Role): never {
  throw new Error(`Contrat du catalogue rompu : « ${field} » absent pour le rôle ${role}`);
}

function amount(raw: ArticleResponse, key: keyof ArticleResponse, role: Role): number | null {
  if (!(key in raw)) contractError(key, role);
  const value = raw[key];
  if (value === null) return null;
  if (typeof value !== "number") contractError(key, role);
  return value;
}

function core(raw: ArticleResponse): ArticleCore {
  return {
    id: raw.id,
    version: raw.version,
    archived: raw.status === "archived",
    name: raw.display_name,
    values: {
      ...raw.attributes,
      name: raw.display_name,
      brand: raw.brand,
      model: raw.model,
      reference: raw.reference,
      unit: raw.stock_unit,
      sold_by_piece: raw.sold_by_piece,
      piece_length_m: raw.piece_length_m,
    },
    alertThreshold: raw.alert_threshold,
    effectiveThreshold: raw.effective_alert_threshold,
    notes: raw.notes,
  };
}

function prices(raw: ArticleResponse, role: Role): SellingPrices {
  return {
    basePrice: amount(raw, "base_price", role),
    minPrice: amount(raw, "min_price", role),
    minPriceActive: raw.min_price_active ?? contractError("min_price_active", role),
    basePricePiece: amount(raw, "base_price_piece", role),
    minPricePiece: amount(raw, "min_price_piece", role),
  };
}

function costs(raw: ArticleResponse, role: Role): Costs {
  return { lastCost: amount(raw, "last_cost", role), wac: amount(raw, "wac", role) };
}

/** Le chauffeur n'a aucun accès au catalogue : demander sa vue est une erreur de garde. */
export function articleView(role: Role, raw: ArticleResponse): ArticleView {
  if (raw.status !== "active" && raw.status !== "archived") {
    throw new Error(`Statut d'article inconnu : « ${raw.status} »`);
  }
  switch (role) {
    case "owner":
      return {
        ...core(raw),
        kind: "owner",
        prices: prices(raw, role),
        costs: costs(raw, role),
        history: raw.price_history ?? null,
      };
    case "accountant":
      return { ...core(raw), kind: "accountant", costs: costs(raw, role) };
    case "seller":
      return { ...core(raw), kind: "seller", prices: prices(raw, role) };
    case "driver":
      throw new Error("Le chauffeur n'a pas accès au catalogue");
  }
}

export function pricesOf(view: ArticleView): SellingPrices | null {
  return view.kind === "accountant" ? null : view.prices;
}

export function costsOf(view: ArticleView): Costs | null {
  return view.kind === "seller" ? null : view.costs;
}
