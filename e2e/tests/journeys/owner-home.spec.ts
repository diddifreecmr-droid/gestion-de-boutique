/**
 * E2E-04 — Accueil propriétaire (données SCN-01) : ventes, encaissé, marge du jour.
 * Débloqué par : T22 (tableau de bord) sur T19, ventes T16 + amorçage T10.
 */
import { SEED_BLOCKED, test } from "../../fixtures/seed";

test.describe("E2E-04 accueil propriétaire", () => {
  test.fixme(true, `T22 (tableau de bord) sur T19 ; ${SEED_BLOCKED}`);

  test("1er écran : 780 000 FCFA, « 1 vente », encaissé 300 000, marge 240 000, « Voir aussi au CMP »", () => {});
  test("barre du bas ≤ 5 entrées ; un appui sur Ventes ouvre V-000001", () => {});
  test("affichage < 2 s après connexion en profil lent (service worker installé)", () => {});
});
