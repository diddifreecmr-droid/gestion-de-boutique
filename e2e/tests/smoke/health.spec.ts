/** (f) Le frontend relaie /api vers le backend jetable (même origine, specs D11). */
import { expect, test } from "@playwright/test";
import { API_PREFIX } from "../../support/env";

test("GET /api/v1/health répond via le proxy du frontend", async ({ request }) => {
  const response = await request.get(`${API_PREFIX}/health`);
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual({ status: "ok" });
});
