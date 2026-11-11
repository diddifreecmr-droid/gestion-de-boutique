/** (d) Échec de connexion : message générique, sans dire si le numéro existe (AUTH, SEC-N). */
import { expect, test } from "@playwright/test";
import { API_PREFIX } from "../../support/env";
import { loginForm, openLogin, UNKNOWN_PHONE, WRONG_PIN } from "../../support/login";

test("numéro inconnu + code : « Numéro ou code incorrect », saisie conservée", async ({ page }) => {
  await openLogin(page);
  const form = loginForm(page);
  await form.phone.fill(UNKNOWN_PHONE);
  await form.pin.fill(WRONG_PIN);
  const login = page.waitForResponse(
    (r) => r.url().endsWith(`${API_PREFIX}/auth/login`) && r.request().method() === "POST",
  );
  await form.submit.click();
  const response = await login;
  expect(response.status()).toBe(401);
  const body: unknown = await response.json();
  expect(body).toMatchObject({ error: { code: expect.any(String) } });
  expect(JSON.stringify(body)).not.toContain("699"); // aucun écho du numéro

  await expect(page.getByText("Numéro ou code incorrect")).toBeVisible();
  await expect(form.pin).toHaveAttribute("aria-invalid", "true");
  await expect(form.phone).toHaveValue(UNKNOWN_PHONE);
  await expect(form.pin).toHaveValue(WRONG_PIN);
  await expect(page).toHaveURL(/\/connexion$/);
});

test("code de 5 chiffres : refusé avant envoi, aucune requête", async ({ page }) => {
  await openLogin(page);
  const form = loginForm(page);
  let sent = false;
  page.on("request", (r) => {
    if (r.url().includes(`${API_PREFIX}/auth/login`)) sent = true;
  });
  await form.phone.fill(UNKNOWN_PHONE);
  await form.pin.fill("12345");
  await form.submit.click();
  await expect(page.getByText("Le code doit avoir 6 chiffres")).toBeVisible();
  expect(sent).toBe(false);
});
