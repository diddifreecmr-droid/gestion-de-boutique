import { screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  NOW,
  preloadPurchasing,
  purchase,
  PURCHASE_ID,
  PURCHASES_PATH,
  purchasingRoutes,
  route,
  setClock,
} from "../../testing/purchasing";
import { sent } from "../../testing/purchasingUi";
import { renderApp } from "../../testing/renderApp";
import { money } from "../../testing/renderSale";
import { FULLY_PAID } from "./correctionRule";

const SHEET = `${PURCHASES_PATH}?vue=fiche&id=${PURCHASE_ID}`;
const GET = route("GET", `/purchases/${PURCHASE_ID}`);
const PAY = route("POST", `/purchases/${PURCHASE_ID}/payments`);
const PAID = purchase({
  paid: 10800000,
  payment_status: "paid",
  payments: [
    {
      id: "pay-1",
      paid_on: "2026-11-10",
      amount: 10800000,
      mode_id: "mode-virement",
      reference: "VIR-889",
      recorded_at: "2026-11-10T09:00:00Z",
      recorded_by: "u",
    },
  ],
});

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

describe("noter un paiement (UC-ACH-06)", () => {
  it("date du jour, montant, mode : envoyé avec un id client, retour à la fiche", async () => {
    const partial = purchase({ paid: 5000000, payment_status: "partially_paid" });
    const { user, fake, container, router } = renderApp(
      SHEET,
      purchasingRoutes("accountant", { [GET]: json(200, purchase()), [PAY]: json(201, partial) }),
    );
    await user.click(await screen.findByRole("button", { name: "Noter un paiement" }));
    expect(await screen.findByLabelText("Montant payé")).toBeVisible();
    expect(screen.getByText(money(10800000))).toBeVisible();
    expect(screen.getByLabelText("Date du paiement")).toHaveValue("2026-11-11");
    expect(screen.getByRole("radio", { name: "Espèces" })).toHaveAttribute("aria-checked", "true");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Noter le paiement" }));
    expect(screen.getByText("Le montant est vide")).toBeVisible();
    await user.type(screen.getByLabelText("Montant payé"), "5000000");
    await user.click(screen.getByRole("button", { name: "Noter le paiement" }));
    expect(await screen.findByText("Paiement noté — A-000012")).toBeVisible();
    const body = sent(fake.calls, "POST", "/payments") as { id: string };
    expect(isUuidV7(body.id)).toBe(true);
    expect(body).toEqual({
      id: body.id,
      amount: 5000000,
      mode_id: "mode-cash",
      paid_on: null,
      reference: null,
    });
    expect(router.state.location.search).toBe(`?vue=fiche&id=${PURCHASE_ID}`);
  });

  it("dépassement : « Reste à payer : … » ; référence exigée par le mode", async () => {
    const over = apiError(422, "OVERPAYMENT", "Trop", {
      total: 10800000,
      paid: 0,
      remaining: 10800000,
    });
    const { user } = renderApp(
      `${PURCHASES_PATH}?vue=paiement&id=${PURCHASE_ID}`,
      purchasingRoutes("accountant", { [GET]: json(200, purchase()), [PAY]: over }),
    );
    await screen.findByLabelText("Montant payé");
    await user.type(screen.getByLabelText("Montant payé"), "20000000");
    await user.click(screen.getByRole("radio", { name: "Virement" }));
    await user.click(screen.getByRole("button", { name: "Noter le paiement" }));
    expect(screen.getByText("La référence est obligatoire pour ce mode")).toBeVisible();
    await user.type(screen.getByLabelText("Référence"), "VIR-1");
    await user.click(screen.getByRole("button", { name: "Noter le paiement" }));
    expect(
      await screen.findByText(
        `Montant trop élevé : il dépasse le total de l'achat. Reste à payer : ${money(10800000)}.`,
        { normalizer: (text) => text.replace(/\s/g, " ") },
      ),
    ).toBeVisible();
  });

  it("achat payé : paiements listés, « Noter un paiement » indisponible avec sa raison", async () => {
    renderApp(SHEET, purchasingRoutes("accountant", { [GET]: json(200, PAID) }));
    const button = await screen.findByRole("button", { name: "Noter un paiement" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveAccessibleDescription(FULLY_PAID);
    expect(screen.getByRole("list", { name: "Paiements notés" })).toHaveTextContent(
      `10/11/2026Virement · VIR-889${money(10800000)}`,
    );
    expect(screen.getByText("Payé", { selector: "span" })).toBeVisible();
  });
});
