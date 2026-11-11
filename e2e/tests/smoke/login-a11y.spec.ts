/**
 * (b) axe : 0 violation « serious » / « critical », `color-contrast` active (A11Y-01, A11Y-07).
 * (c) Zones de toucher ≥ 48 × 48 px et ≥ 8 px entre deux cibles (A11Y-02).
 */
import { expect, test } from "@playwright/test";
import { blockingViolations } from "../../support/axe";
import { MOBILE_ONLY } from "../../support/env";
import { tooClose, touchTargets, undersized } from "../../support/layout";
import { loginForm, openLogin, UNKNOWN_PHONE } from "../../support/login";

/**
 * DÉFAUT CONNU (signalé à @frontend, non corrigé ici) : le lien texte sous le formulaire
 * (`LoginPage.tsx`, classes `text-label … underline`, sans hauteur minimale) mesure
 * 328 × 24 px à 360 px de large ; attendu ≥ 48 px de haut (design-system.md § 8).
 * `test.fail` : le test échouera (« passé de façon inattendue ») dès la correction → retirer.
 */
const SMALL_LINK_DEFECT =
  "Défaut A11Y-02 : lien d'écran de connexion de 24 px de haut (attendu ≥ 48 px) — LoginPage.tsx";

const SCREENS = [
  { path: "/connexion", heading: "Connexion", link: "Connexion administrateur plateforme" },
  {
    path: "/connexion/admin",
    heading: "Connexion administrateur",
    link: "Retour à la connexion des boutiques",
  },
] as const;

test.describe("écran de connexion — accessibilité", () => {
  test("axe : aucune violation serious/critical (contraste compris)", async ({ page }) => {
    await openLogin(page);
    expect(await blockingViolations(page)).toEqual([]);
  });

  test("axe : aucune violation avec les erreurs de champ affichées", async ({ page }) => {
    await openLogin(page);
    await loginForm(page).submit.click();
    await expect(page.getByText("Le numéro est vide")).toBeVisible();
    expect(await blockingViolations(page)).toEqual([]);
  });

  test("axe : connexion administrateur", async ({ page }) => {
    await page.goto("/connexion/admin");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Connexion administrateur");
    expect(await blockingViolations(page)).toEqual([]);
  });

  for (const screen of SCREENS) {
    test(`${screen.path} : zones de toucher ≥ 48 × 48 px ${MOBILE_ONLY}`, async ({ page }) => {
      test.fail(true, SMALL_LINK_DEFECT);
      await page.goto(screen.path);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(screen.heading);
      await expect(page.getByRole("link", { name: screen.link })).toBeVisible();
      const targets = await touchTargets(page);
      expect(targets.length).toBeGreaterThanOrEqual(4); // 2 champs, 1 bouton, 1 lien
      expect(undersized(targets)).toEqual([]);
    });
  }

  test(`champs et bouton ≥ 48 px (hors lien connu) ${MOBILE_ONLY}`, async ({ page }) => {
    await openLogin(page);
    const targets = (await touchTargets(page)).filter((t) => !t.description.startsWith("<a>"));
    expect(targets.length).toBeGreaterThanOrEqual(3);
    expect(undersized(targets)).toEqual([]);
  });

  test(`au moins 8 px entre deux cibles ${MOBILE_ONLY}`, async ({ page }) => {
    await openLogin(page);
    await loginForm(page).phone.fill(UNKNOWN_PHONE);
    expect(tooClose(await touchTargets(page))).toEqual([]);
  });
});
