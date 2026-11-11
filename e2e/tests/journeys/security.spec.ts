/**
 * Non-fuite des coûts (A4, SEC-N05) et isolation des boutiques (A5, E2E-09), vues du navigateur.
 */
import { SEED_BLOCKED, test } from "../../fixtures/seed";

test.describe("SEC-N05 non-fuite des coûts (vendeur)", () => {
  test.fixme(true, `T20/T21 (écrans Stock, Vente) ; ${SEED_BLOCKED}`);

  // Écouter page.on("response") : aucune clé cost / cmp / margin / value ; idem dans le DOM.
  test("aucun coût, CMP, marge ni valeur dans les réponses ni le DOM des écrans du vendeur", () => {});
});

test.describe("A5 / E2E-09 isolation des boutiques", () => {
  test.fixme(true, `${SEED_BLOCKED} (deux boutiques, deux propriétaires, un utilisateur à deux rôles)`);

  test("URL /s/{B} forgée par un utilisateur de A : refus, aucune donnée de B", () => {});
  test("changement de boutique : menu vendeur → menu comptable, aucune donnée de A dans B", () => {});
});
