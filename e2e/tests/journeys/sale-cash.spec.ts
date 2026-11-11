/**
 * E2E-01 — Vente comptant en 4 gestes, < 30 s sur 360 px (A1, recette § 5).
 * Débloqué par : T21 (écran Nouvelle vente) + amorçage T10 (boutique A, vendeur V, article HJ).
 */
import { MOBILE_ONLY } from "../../support/env";
import { expect, SEED_BLOCKED, test } from "../../fixtures/seed";

test.describe("E2E-01 vente comptant (A1)", () => {
  test.fixme(true, `T21 (écran Nouvelle vente) ; ${SEED_BLOCKED}`);

  test(`≤ 4 gestes après l'ouverture, < 30 s ${MOBILE_ONLY}`, async ({ page, shopA }) => {
    const started = Date.now();
    await page.goto(`/s/${shopA.shopId}`);
    await page.getByRole("link", { name: "Nouvelle vente" }).click();
    // (1) « hao » + suggestion — (2) prix 780 000 gardé — (3) Espèces présélectionné — (4) Valider
    await page.getByLabel("Article").fill("hao");
    await page.getByRole("option", { name: "Haojue HJ125-8" }).click();
    await expect(page.getByLabel("Prix")).toHaveAttribute("inputmode", "numeric");
    await expect(page.getByText("Stock disponible à Garoua : 20")).toBeVisible();
    await page.getByRole("button", { name: "Valider la vente" }).click();
    await expect(page.getByText("Vente enregistrée — reçu n° V-000001")).toBeVisible();
    expect(Date.now() - started).toBeLessThan(30_000);
  });

  test("profil réseau lent : ouverture → toast < 10 s (médiane de 5), Valider → toast < 2 s", () => {
    // CDP Network.emulateNetworkConditions (300 ms, 700/300 kbit/s) + Emulation.setCPUThrottlingRate(4).
  });
});
