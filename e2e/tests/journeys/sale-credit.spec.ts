/**
 * E2E-02 — Vente à crédit ; E2E-03 — Versement (recette § 5, SCN-07).
 * Débloqué par : T21 (écrans Ventes, Créances) sur T16/T17 + amorçage T10.
 */
import { SEED_BLOCKED, test } from "../../fixtures/seed";

test.describe("E2E-02 vente à crédit", () => {
  test.fixme(true, `T21 (Ventes) sur T16/T17 ; ${SEED_BLOCKED}`);

  test("client nouveau, acompte 300 000 Espèces : « Reste à payer : 480 000 », reçu « Vente à crédit »", () => {});
  test("sans client : message sous le champ, aucun envoi", () => {});
});

test.describe("E2E-03 versement", () => {
  test.fixme(true, `T21 (Créances) sur T17 ; ${SEED_BLOCKED}`);

  test("200 000 OM : « Reste à payer après ce versement : 280 000 FCFA », reçu R-000001", () => {});
  test("300 000 > reste : erreur sous le champ (aria-live), rien d'envoyé ou 422 traduit", () => {});
});
