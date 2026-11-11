/**
 * Données de la passerelle simulée (boutique « Motos Garoua »). Déterministes : les tests et
 * la vitrine s'appuient dessus. Aucune donnée de coût n'existe ici (TR-05).
 */
import type { PaymentMode, SaleLocation } from "../catalogContract";
import type { CustomerSummary } from "../salesContract";

export const GAROUA: SaleLocation = { id: "loc-garoua", name: "Garoua" };
export const NGAOUNDERE: SaleLocation = { id: "loc-ngaoundere", name: "Ngaoundéré" };
export const BOULAI: SaleLocation = { id: "loc-boulai", name: "Dépôt Garoua-Boulaï" };
export const LOCATIONS: readonly SaleLocation[] = [GAROUA, NGAOUNDERE, BOULAI];

function mode(id: string, name: string, order: number): PaymentMode {
  return { id, name, reference_required: false, active: true, display_order: order, version: 1 };
}

export const PAYMENT_MODES: readonly PaymentMode[] = [
  mode("pm-cash", "Espèces", 1),
  mode("pm-orange", "Orange Money", 2),
  mode("pm-mtn", "MTN MoMo", 3),
  mode("pm-transfer", "Virement", 4),
  mode("pm-cheque", "Chèque", 5),
];

export interface SeedArticle {
  id: string;
  name: string;
  base_price: number;
  /** Minimum appliqué par le « serveur » simulé. */
  min_price: number;
  /** Faux si le minimum n'est pas communiqué au client (le serveur le fait respecter). */
  min_price_shared: boolean;
  /** Rang « plus vendus » (1 = le plus vendu) ; null = jamais classé. */
  rank: number | null;
  /** Stock réel par lieu (entiers). */
  stock: Readonly<Record<string, number>>;
  /**
   * Stock affiché par le catalogue à Garoua s'il diffère du réel : simule une vente faite
   * entre-temps sur un autre téléphone (le serveur répond alors STOCK_INSUFFICIENT).
   */
  listed_at_garoua?: number;
}

function stock(garoua: number, ngaoundere: number, boulai: number): Record<string, number> {
  return { [GAROUA.id]: garoua, [NGAOUNDERE.id]: ngaoundere, [BOULAI.id]: boulai };
}

export const ARTICLES: readonly SeedArticle[] = [
  {
    id: "art-hj125-8",
    name: "Haojue HJ125-8",
    base_price: 780_000,
    min_price: 720_000,
    min_price_shared: true,
    rank: 1,
    stock: stock(4, 6, 12),
  },
  {
    id: "art-sy125-8",
    name: "Sanya SY125-8",
    base_price: 650_000,
    min_price: 600_000,
    min_price_shared: true,
    rank: 2,
    stock: stock(7, 2, 0),
  },
  {
    id: "art-nf125-2",
    name: "Nanfang NF125-2",
    base_price: 620_000,
    min_price: 580_000,
    min_price_shared: true,
    rank: 3,
    stock: stock(1, 0, 4),
  },
  {
    id: "art-dk150",
    name: "Haojue DK150",
    base_price: 950_000,
    min_price: 900_000,
    min_price_shared: true,
    rank: 4,
    stock: stock(0, 2, 0),
  },
  {
    id: "art-sy150-3",
    name: "Sanya SY150-3",
    base_price: 720_000,
    min_price: 680_000,
    min_price_shared: false,
    rank: 5,
    stock: stock(3, 1, 0),
  },
  {
    id: "art-hj150-10",
    name: "Haojue HJ150-10",
    base_price: 890_000,
    min_price: 850_000,
    min_price_shared: true,
    rank: null,
    stock: stock(1, 3, 0),
    listed_at_garoua: 2,
  },
  {
    id: "art-nf150",
    name: "Nanfang NF150",
    base_price: 700_000,
    min_price: 650_000,
    min_price_shared: true,
    rank: null,
    stock: stock(2, 0, 5),
  },
  {
    id: "art-jc125",
    name: "Jincheng JC125",
    base_price: 590_000,
    min_price: 550_000,
    min_price_shared: true,
    rank: null,
    stock: stock(6, 1, 3),
  },
];

export interface SeedCustomer extends CustomerSummary {
  /** Dette en cours, pour CREDIT_LIMIT_EXCEEDED (le plafond est `credit_limit`). */
  debt: number;
}

function customer(
  id: string,
  name: string,
  phone: string,
  extra: Partial<SeedCustomer> = {},
): SeedCustomer {
  return {
    id,
    name,
    phone,
    kind: "individual",
    city: null,
    address: null,
    id_doc_type: null,
    id_doc_number: null,
    id_doc_photo_id: null,
    credit_limit: null,
    note: null,
    created_by: "vitrine",
    version: 1,
    debt: 0,
    ...extra,
  };
}

export const CUSTOMERS: readonly SeedCustomer[] = [
  customer("cus-moussa", "Moussa Abdou", "+237690000000"),
  customer("cus-garba", "Garba Transport SARL", "+237677112233", {
    kind: "company",
    credit_limit: 500_000,
    debt: 300_000,
  }),
  customer("cus-aissatou", "Aïssatou Bello", "+237699887766", { debt: 120_000 }),
];

/** Châssis déjà vendu (RG-M01) et la vente qui le porte. */
export const SOLD_CHASSIS: Readonly<Record<string, string>> = { LBXPCJ0A1N0001234: "V-000098" };

/** Premier numéro attribué : V-000124 (CDC § 1.3). */
export const FIRST_SALE_NUMBER = 124;
