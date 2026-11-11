/**
 * (e) Coupure réseau (A6, TR-26) : bannière « Connexion nécessaire », formulaire conservé,
 * rien mis en file ; au retour du réseau, la bannière disparaît.
 */
import { expect, test } from "@playwright/test";
import { loginForm, openLogin, UNKNOWN_PHONE, WRONG_PIN } from "../../support/login";

test("hors ligne : bannière « Connexion nécessaire », saisie gardée", async ({ page, context }) => {
  await openLogin(page);
  const form = loginForm(page);
  await form.phone.fill(UNKNOWN_PHONE);
  await form.pin.fill(WRONG_PIN);

  const queued: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/sync")) queued.push(r.url());
  });
  await context.setOffline(true);
  const banner = page.getByRole("status").filter({ hasText: "Connexion nécessaire" });
  await expect(banner).toBeVisible();

  await form.submit.click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Connexion nécessaire : vérifiez le réseau" }),
  ).toBeVisible();
  await expect(form.phone).toHaveValue(UNKNOWN_PHONE);
  await expect(form.pin).toHaveValue(WRONG_PIN);

  expect(queued, "aucune mise en file (offline_capture inactif)").toEqual([]);

  await context.setOffline(false);
  await expect(banner).toBeHidden();
});
