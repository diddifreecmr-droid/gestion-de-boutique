/** État en mémoire partagé par les passerelles simulées (catalogue et ventes). */
import type { Role } from "../../auth/me";
import { NetworkError } from "../../api/errors";
import type { RecordSaleCommand, SaleResult } from "../salesContract";
import {
  ARTICLES,
  CUSTOMERS,
  FIRST_SALE_NUMBER,
  SOLD_CHASSIS,
  type SeedArticle,
  type SeedCustomer,
} from "./seed";

export interface SimulationOptions {
  /** Réseau disponible ? Faux → `NetworkError`, comme le vrai client (aucune file, TR-26). */
  isOnline: () => boolean;
  /** Rôle de l'utilisateur dans la boutique (le vrai serveur le lit dans le jeton). */
  roleIn: (shopId: string) => Role;
  /** Appelé quand un envoi échoue faute de réseau (le bandeau « Connexion nécessaire »). */
  onNetworkFailure?: () => void;
  /** Délai simulé de chaque appel, en ms (0 par défaut : tests déterministes). */
  latencyMs?: number;
}

export interface World {
  options: SimulationOptions;
  articles: Map<string, SeedArticle & { stock: Record<string, number> }>;
  customers: SeedCustomer[];
  soldChassis: Map<string, string>;
  /** Ventes déjà enregistrées, par `id` (idempotence : rejouer renvoie la même vente). */
  sales: Map<string, { command: RecordSaleCommand; result: SaleResult }>;
  nextNumber: number;
  /** Demandes d'accord en attente (le propriétaire ne répond jamais dans la simulation). */
  priceRequests: Set<string>;
}

export function createWorld(options: SimulationOptions): World {
  return {
    options,
    articles: new Map(
      ARTICLES.map((article) => [article.id, { ...article, stock: { ...article.stock } }]),
    ),
    customers: CUSTOMERS.map((customer) => ({ ...customer })),
    soldChassis: new Map(Object.entries(SOLD_CHASSIS)),
    sales: new Map(),
    nextNumber: FIRST_SALE_NUMBER,
    priceRequests: new Set(),
  };
}

/** Prologue de chaque appel : latence éventuelle, puis contrôle du réseau. */
export async function reach(world: World): Promise<void> {
  const delay = world.options.latencyMs ?? 0;
  if (delay > 0) {
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
  if (!world.options.isOnline()) {
    world.options.onNetworkFailure?.();
    throw new NetworkError("Serveur injoignable : connexion nécessaire");
  }
}

export function requireArticle(world: World, articleId: string) {
  const article = world.articles.get(articleId);
  if (article === undefined) throw new Error(`Simulation : article inconnu « ${articleId} »`);
  return article;
}

export function saleNumber(value: number): string {
  return `V-${String(value).padStart(6, "0")}`;
}
