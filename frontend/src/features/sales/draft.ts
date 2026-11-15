/**
 * Brouillon de la vente, tel que l'écran le tient. Il n'est jamais effacé par un échec
 * d'envoi : « Connexion nécessaire » laisse tout en place pour renvoyer d'un appui.
 */
import { uuidV7 } from "../../core/api/uuidv7";
import type { CatalogArticle } from "../../core/gateways/catalogContract";
import type { CustomerKind, CustomerSummary, SaleMode } from "../../core/gateways/salesContract";
import { capped, statusOf } from "./saleStock";
import { toTenths } from "./textile";

/** Choix « À crédit » parmi les modes de paiement (ce n'est pas un mode de la boutique). */
export const CREDIT_CHOICE = "credit";

export interface UnitDetail {
  color: string;
  chassis: string;
  engine: string;
}

export interface LineDraft {
  key: string;
  article: CatalogArticle;
  /**
   * Borne de la quantité : stock du lieu dans l'unité de stock (entier à l'unité, en mètres au
   * mètre), ou `null` quand la vente n'est jamais refusée pour manque de stock (2026-11-15).
   */
  available: number | null;
  /** Mode de la ligne : à l'unité, ou « Au mètre / À la pièce » (Textile, § 7.5). */
  mode: SaleMode;
  /** Unités vendues ; à la pièce : nombre de pièces ; au mètre : inutilisé (1). */
  quantity: number;
  /** Longueur saisie au mètre (« 2,5 »), lue par `parseLength` ; vide sinon. */
  length: string;
  unitPrice: number | null;
  /** Une entrée par unité (CDC § 17.3), toujours de longueur `quantity`. */
  units: UnitDetail[];
}

export type CustomerDraft =
  | { mode: "none" }
  | { mode: "existing"; customer: CustomerSummary }
  | { mode: "new"; name: string; phone: string; kind: CustomerKind };

export interface SaleDraft {
  /** Identifiant UUIDv7 de la vente : le même à chaque renvoi (idempotence, specs § 6.1). */
  saleId: string;
  lines: LineDraft[];
  /** Mode choisi (`mode_id`) ou CREDIT_CHOICE. */
  payment: string | null;
  /** Répartition sur plusieurs modes (`mode_id` → montant) ; null = un seul mode. */
  split: Record<string, number | null> | null;
  cashGiven: number | null;
  reference: string;
  customer: CustomerDraft;
  deposit: number | null;
  depositMode: string | null;
  reminderOn: string;
  terms: string;
  note: string;
  /** Minimums révélés par le serveur (PRICE_BELOW_MINIMUM) quand le catalogue les taisait. */
  serverMinimums: Record<string, number>;
  /**
   * Le serveur a exigé l'accord (`request_required`) alors que l'écran lisait le réglage
   * désactivé (changé entre-temps) : l'écran passe au parcours « Demander l'accord ».
   */
  approvalRequired: boolean;
}

export const EMPTY_UNIT: UnitDetail = { color: "", chassis: "", engine: "" };

export function newDraft(payment: string | null): SaleDraft {
  return {
    saleId: uuidV7(),
    lines: [],
    payment,
    split: null,
    cashGiven: null,
    reference: "",
    customer: { mode: "none" },
    deposit: null,
    depositMode: payment,
    reminderOn: "",
    terms: "",
    note: "",
    serverMinimums: {},
    approvalRequired: false,
  };
}

/** Chiffre du stock ; l'appeler sans chiffre servi (stock réservé au gérant) est une erreur. */
function counted(article: CatalogArticle): string {
  if (article.available === null) {
    throw new Error(`« ${article.name} » : aucun chiffre de stock pour cet acteur`);
  }
  return article.available;
}

/** Stock d'un article vendu à l'unité : un entier (« 4 », « 4.000 », « -2 » vendu sans stock). */
export function unitStock(article: CatalogArticle): number {
  const value = counted(article);
  if (!/^-?\d+(\.0+)?$/.test(value)) {
    throw new Error(`Stock non entier pour « ${article.name} » : « ${value} »`);
  }
  return Number(value);
}

/** Stock d'un article au mètre, en dixièmes (« 54.900 » → 549, « -1.5 » → -15). */
export function meterStock(article: CatalogArticle): number {
  const value = counted(article);
  return value.startsWith("-") ? -toTenths(value.slice(1)) : toTenths(value);
}

/** L'article a-t-il du stock à vendre ici (1 unité, 0,1 m au mètre, ou pastille hors rupture) ? */
export function inStock(article: CatalogArticle): boolean {
  if (article.available === null) return statusOf(article, true) !== "out";
  if (article.sale_mode === "meter") return meterStock(article) > 0;
  if (article.sale_mode === "unit") return unitStock(article) >= 1;
  throw new Error(`« ${article.name} » : mode de vente « ${article.sale_mode} » sans ligne`);
}

/** Borne de la ligne : stock du lieu (Motos), ou `null` quand la vente passe sans stock. */
function capOf(article: CatalogArticle): number | null {
  if (!capped(article)) return null;
  return article.sale_mode === "meter" ? meterStock(article) / 10 : unitStock(article);
}

export function newLine(article: CatalogArticle): LineDraft {
  if (capped(article) && !inStock(article)) {
    throw new Error(`« ${article.name} » est en rupture : ligne impossible`);
  }
  return {
    key: uuidV7(),
    article,
    available: capOf(article),
    mode: article.sale_mode,
    quantity: 1,
    length: "",
    unitPrice: article.base_price,
    units: [{ ...EMPTY_UNIT }],
  };
}

/** Change la quantité et garde une fiche de détail par unité (les saisies déjà faites restent). */
export function withQuantity(line: LineDraft, quantity: number): LineDraft {
  const units = Array.from(
    { length: quantity },
    (_, index) => line.units[index] ?? { ...EMPTY_UNIT },
  );
  return { ...line, quantity, units };
}

/** Prix de base et minimum de l'unité choisie (le mètre, ou la pièce, § 7.5). */
export function pricesOf(line: Pick<LineDraft, "article" | "mode">) {
  if (line.mode !== "piece") {
    return { base: line.article.base_price, minimum: line.article.min_price };
  }
  const piece = line.article.piece;
  if (piece === undefined) throw new Error(`« ${line.article.name} » ne se vend pas à la pièce`);
  return { base: piece.base_price, minimum: piece.min_price };
}

/**
 * Bascule « Au mètre / À la pièce » : le prix de base de l'unité choisie est pré-rempli (il
 * reste modifiable) ; à la pièce, une pièce.
 */
export function withMode(line: LineDraft, mode: "meter" | "piece"): LineDraft {
  if (line.mode === mode) return line;
  const next = { ...line, mode, quantity: 1 };
  return { ...next, unitPrice: pricesOf(next).base };
}

/** Minimum connu pour la ligne : celui du catalogue, sinon celui que le serveur a révélé. */
export function minimumOf(draft: SaleDraft, line: LineDraft): number | null {
  return pricesOf(line).minimum ?? draft.serverMinimums[line.article.id] ?? null;
}
