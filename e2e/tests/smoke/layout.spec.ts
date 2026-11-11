/** (a) L'application se charge à 360 px sans défilement horizontal (recette A11Y-06, CDC § 21). */
import { expect, test } from "@playwright/test";
import { MOBILE_ONLY } from "../../support/env";
import { pageWidth } from "../../support/layout";
import { openLogin } from "../../support/login";

test(`chargement à 360 px : aucun défilement horizontal ${MOBILE_ONLY}`, async ({ page }) => {
  await page.goto("/");
  // Sans session, « / » mène à la connexion.
  await expect(page).toHaveURL(/\/connexion$/);
  await openLogin(page);
  const { scrollWidth, clientWidth } = await pageWidth(page);
  expect(clientWidth).toBe(360);
  expect(scrollWidth, `scrollWidth ${String(scrollWidth)} > clientWidth ${String(clientWidth)}`)
    .toBeLessThanOrEqual(clientWidth);
});

test("connexion administrateur : aucun défilement horizontal", async ({ page }) => {
  await page.goto("/connexion/admin");
  await expect(page.getByRole("heading", { level: 1, name: "Connexion administrateur" })).toBeVisible();
  const { scrollWidth, clientWidth } = await pageWidth(page);
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
});
