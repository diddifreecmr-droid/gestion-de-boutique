import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { Purchase } from "../../core/gateways/purchasingContract";
import { apiError, json } from "../../testing/fakeApi";
import {
  HAOJUE_ID,
  NOW,
  preloadPurchasing,
  purchase,
  PURCHASE_ID,
  PURCHASES_PATH,
  purchasingRoutes,
  route,
  setClock,
  withArticleSearch,
} from "../../testing/purchasing";
import { lineGroup, sent } from "../../testing/purchasingUi";
import { renderApp } from "../../testing/renderApp";
import { REASON_EMPTY } from "./PurchaseForm";
import { STOCK_LEFT_MESSAGE } from "./purchaseErrors";

const EDIT = `${PURCHASES_PATH}?vue=corriger&id=${PURCHASE_ID}`;
const GET = route("GET", `/purchases/${PURCHASE_ID}`);
const PATCH = route("PATCH", `/purchases/${PURCHASE_ID}`);
const save = () => screen.getByRole("button", { name: "Enregistrer la correction" });

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

function open(patch: Purchase | Response, role: "owner" | "accountant" = "accountant") {
  const reply = patch instanceof Response ? patch : json(200, patch);
  return renderApp(
    EDIT,
    withArticleSearch(purchasingRoutes(role, { [GET]: json(200, purchase()), [PATCH]: reply })),
  );
}

async function changeQuantity(user: ReturnType<typeof open>["user"], quantity: string) {
  const line = await screen.findByRole("group", { name: "Ligne 1" });
  const field = within(line).getByLabelText("Quantité");
  expect(field).toHaveValue("20");
  await user.clear(field);
  await user.type(field, quantity);
}

describe("corriger un achat (UC-ACH-03)", () => {
  it("motif obligatoire ; seuls les champs changés partent, avec la version", async () => {
    const { user, fake, router } = open(purchase({ version: 2 }));
    await changeQuantity(user, "18");
    expect(screen.getByText("Haojue Douala")).toBeVisible();
    expect(screen.getByRole("radio", { name: "Garoua-Boulaï" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.queryByRole("radio", { name: "Lieu de réception habituel" })).toBeNull();
    await user.click(save());
    expect(screen.getByText(REASON_EMPTY)).toBeVisible();
    expect(fake.count(PATCH)).toBe(0);

    await user.type(screen.getByLabelText("Motif de la correction"), "2 motos comptées en trop");
    await user.click(save());
    expect(await screen.findByText("Achat corrigé — A-000012")).toBeVisible();
    expect(sent(fake.calls, "PATCH", `/purchases/${PURCHASE_ID}`)).toEqual({
      version: 1,
      reason: "2 motos comptées en trop",
      confirm_price_gap: false,
      lines: [{ article_id: HAOJUE_ID, quantity: "18", unit: "UNIT", unit_price: 520000 }],
    });
    expect(router.state.location.search).toBe(`?vue=fiche&id=${PURCHASE_ID}`);
  });

  it("marchandise déjà sortie : refus expliqué, la saisie reste", async () => {
    const { user } = open(apiError(422, "STOCK_ALREADY_LEFT", "Déjà sorti", { left: "5" }));
    await changeQuantity(user, "2");
    await user.type(screen.getByLabelText("Motif de la correction"), "Erreur");
    await user.click(save());
    expect(await screen.findByText(STOCK_LEFT_MESSAGE)).toBeVisible();
    expect(within(lineGroup(1)).getByLabelText("Quantité")).toHaveValue("2");
  });

  it("délai du comptable dépassé au serveur : date limite affichée", async () => {
    const closed = apiError(422, "CORRECTION_WINDOW_CLOSED", "Délai", { last_day: "2026-11-18" });
    const { user } = open(closed);
    await changeQuantity(user, "19");
    await user.type(screen.getByLabelText("Motif de la correction"), "Erreur");
    await user.click(save());
    expect(
      await screen.findByText(
        "Délai dépassé : le comptable pouvait corriger cet achat jusqu'au 18/11/2026. Demandez au propriétaire.",
      ),
    ).toBeVisible();
  });

  it("conflit de version : relire la fiche", async () => {
    const { user } = open(apiError(409, "VERSION_CONFLICT", "Conflit"));
    await changeQuantity(user, "19");
    await user.type(screen.getByLabelText("Motif de la correction"), "Erreur");
    await user.click(save());
    expect(await screen.findByText(/modifié cet achat entre-temps/)).toBeVisible();
  });

  it("comptable après J+7 : l'écran de correction n'ouvre pas la saisie", async () => {
    setClock("2026-11-20T10:00:00Z");
    open(purchase());
    expect(
      await screen.findByText(
        "Corrigeable par le comptable jusqu'au 18/11/2026 — demandez au propriétaire",
      ),
    ).toBeVisible();
    expect(screen.queryByLabelText("Motif de la correction")).toBeNull();
  });
});
