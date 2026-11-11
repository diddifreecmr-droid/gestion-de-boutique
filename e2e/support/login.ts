/** Écran de connexion (frontend/src/features/auth/LoginPage.tsx) : sélecteurs accessibles. */
import { expect, type Page } from "@playwright/test";

export const LOGIN_PATH = "/connexion";

/** Numéro camerounais valide (9 chiffres, mobile) qu'aucun compte ne porte. */
export const UNKNOWN_PHONE = "699 00 00 01";
export const WRONG_PIN = "482915";

export function loginForm(page: Page) {
  return {
    phone: page.getByLabel("Numéro de téléphone"),
    pin: page.getByLabel("Code secret"),
    submit: page.getByRole("button", { name: "Se connecter" }),
  };
}

/** Ouvre /connexion et attend l'écran (la restauration de session a échoué : pas de cookie). */
export async function openLogin(page: Page): Promise<void> {
  await page.goto(LOGIN_PATH);
  await expect(page.getByRole("heading", { level: 1, name: "Connexion" })).toBeVisible();
}
