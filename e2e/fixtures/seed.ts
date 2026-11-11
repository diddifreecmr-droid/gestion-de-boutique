/**
 * Amorçage des données de recette (JDD-0 : boutique A « Motos Garoua », O, V, V2, C, CH ;
 * boutique témoin B, recette-lot1.md en tête).
 *
 * Mécanisme prévu : `seed/seed.py` (hors dépôt de production, lancé par `uv run --project
 * ../backend`) crée l'administrateur plateforme puis tout le reste passe par l'API publique
 * du backend jetable (`POST /platform/shops`, membres, catalogue…), comme un vrai client.
 * Persistance mémoire : les données vivent dans le processus uvicorn, donc rien ne peut être
 * écrit « à côté » ; seule l'API (ou une commande du backend) peut amorcer.
 *
 * BLOQUÉ — amorçage : T10. Il n'existe aujourd'hui ni commande ni route pour créer le premier
 * administrateur plateforme, et `POST /platform/shops` l'exige. Aucun contournement (écriture
 * directe dans les dépôts internes) n'est fait : les parcours qui ont besoin de données sont
 * `test.fixme(SEED_BLOCKED)`. La fixture échoue explicitement si on l'utilise quand même.
 */
import { test as base } from "@playwright/test";

export const SEED_BLOCKED =
  "amorçage : T10 — aucune commande/route ne crée l'administrateur plateforme exigé par POST /platform/shops";

/** Identifiants d'une boutique amorcée (forme cible, à confirmer avec T10). */
export interface SeededShop {
  shopId: string;
  ownerPhone: string;
  ownerPin: string;
  sellerPhone: string;
  sellerPin: string;
}

export const test = base.extend<{ shopA: SeededShop; shopB: SeededShop }>({
  shopA: async ({}, use) => {
    void use;
    throw new Error(`Fixture shopA indisponible (${SEED_BLOCKED})`);
  },
  shopB: async ({}, use) => {
    void use;
    throw new Error(`Fixture shopB indisponible (${SEED_BLOCKED})`);
  },
});

export { expect } from "@playwright/test";
