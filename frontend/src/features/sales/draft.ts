/**
 * Brouillon de la vente, tel que l'écran le tient. Il n'est jamais effacé par un échec
 * d'envoi : « Connexion nécessaire » laisse tout en place pour renvoyer d'un appui.
 */
import { uuidV7 } from "../../core/api/uuidv7";
import type { CatalogArticle } from "../../core/gateways/catalogContract";
import type { CustomerKind, CustomerSummary } from "../../core/gateways/salesContract";

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
  /** Stock du lieu, entier (vente à l'unité). */
  available: number;
  quantity: number;
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

/** Stock d'un article vendu à l'unité : un entier (« 4 » ou « 4.000 »), sinon incohérent. */
export function unitStock(article: CatalogArticle): number {
  if (!/^\d+(\.0+)?$/.test(article.available)) {
    throw new Error(`Stock non entier pour « ${article.name} » : « ${article.available} »`);
  }
  return Number(article.available);
}

export function newLine(article: CatalogArticle): LineDraft {
  const available = unitStock(article);
  if (available < 1) throw new Error(`« ${article.name} » est en rupture : ligne impossible`);
  return {
    key: uuidV7(),
    article,
    available,
    quantity: 1,
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

/** Minimum connu pour la ligne : celui du catalogue, sinon celui que le serveur a révélé. */
export function minimumOf(draft: SaleDraft, line: LineDraft): number | null {
  return line.article.min_price ?? draft.serverMinimums[line.article.id] ?? null;
}
