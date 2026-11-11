import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  NOW,
  OWNER_ID,
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
import { REASON_REQUIRED } from "../../shared/ui";
import { STOCK_LEFT_MESSAGE } from "./purchaseErrors";

const SHEET = `${PURCHASES_PATH}?vue=fiche&id=${PURCHASE_ID}`;
const GET = route("GET", `/purchases/${PURCHASE_ID}`);
const CANCEL = route("POST", `/purchases/${PURCHASE_ID}/cancel`);

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

function firstLine() {
  const [line] = purchase().lines;
  if (line === undefined) throw new Error("achat de test sans ligne");
  return line;
}

const correct = () => screen.getByRole("button", { name: "Corriger l'achat" });

describe("fiche d'un achat (UC-ACH-05)", () => {
  it("lignes avec coût unitaire final, frais, reste à payer, statut « À payer »", async () => {
    const { container } = renderApp(
      SHEET,
      purchasingRoutes("accountant", { [GET]: json(200, purchase()) }),
    );
    expect(await screen.findByRole("heading", { name: "Achat A-000012" })).toBeVisible();
    const lines = screen.getByRole("region", { name: "Articles" });
    expect(lines).toHaveTextContent(`Haojue HJ125-820 × ${money(520000)}`);
    expect(lines).toHaveTextContent(`Part des frais${money(400000)}`);
    expect(lines).toHaveTextContent(`Coût unitaire final${money(540000)} par unité`);
    expect(screen.getByRole("region", { name: "Frais" })).toHaveTextContent(
      `Douane${money(400000)}`,
    );
    expect(screen.getByRole("region", { name: "Achat" })).toHaveTextContent(
      "FournisseurHaojue Douala",
    );
    expect(screen.getByRole("region", { name: "Paiements" })).toHaveTextContent(
      `Reste à payer${money(10800000)}`,
    );
    expect(screen.getByText("À payer")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Annuler l'achat" })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("tissu en yards : quantité saisie et quantité de stock en mètres", async () => {
    const line = {
      ...firstLine(),
      quantity: "10",
      unit: "YARD",
      stock_quantity: "9.1",
      stock_unit: "METER",
      unit_price: 3000,
      total: 30000,
      fee_share: 0,
      final_unit_cost: 3297,
    };
    renderApp(
      SHEET,
      purchasingRoutes("accountant", { [GET]: json(200, purchase({ lines: [line], fees: [] })) }),
    );
    const lines = await screen.findByRole("region", { name: "Articles" });
    expect(lines).toHaveTextContent(`10 yd × ${money(3000)}`);
    expect(lines).toHaveTextContent("Quantité en stocksoit 9,1 m");
    expect(lines).toHaveTextContent(`${money(3297)} par mètre`);
  });
});

describe("corriger (UC-ACH-03)", () => {
  it("comptable après J+7 : « Corriger » indisponible avec sa raison (jour métier de Douala)", async () => {
    setClock("2026-11-18T23:30:00Z"); // 19/11 à 0 h 30 à Douala
    renderApp(SHEET, purchasingRoutes("accountant", { [GET]: json(200, purchase()) }));
    await screen.findByRole("heading", { name: "Achat A-000012" });
    expect(correct()).toHaveAttribute("aria-disabled", "true");
    expect(correct()).toHaveAccessibleDescription(
      "Corrigeable par le comptable jusqu'au 18/11/2026 — demandez au propriétaire",
    );
  });

  it("comptable le dernier jour, propriétaire toujours", async () => {
    setClock("2026-11-18T22:30:00Z"); // 18/11 à 23 h 30 à Douala
    const first = renderApp(
      SHEET,
      purchasingRoutes("accountant", { [GET]: json(200, purchase()) }),
    );
    await screen.findByRole("heading", { name: "Achat A-000012" });
    expect(correct()).not.toHaveAttribute("aria-disabled");
    first.unmount();
    setClock("2027-02-01T10:00:00Z");
    renderApp(
      SHEET,
      purchasingRoutes("owner", { [GET]: json(200, purchase({ cancellable: true })) }),
    );
    await screen.findByRole("heading", { name: "Achat A-000012" });
    expect(correct()).not.toHaveAttribute("aria-disabled");
  });
});

describe("annuler (UC-ACH-04, propriétaire)", () => {
  it("motif obligatoire, puis l'achat reste visible, annulé", async () => {
    const cancelled = purchase({
      status: "cancelled",
      cancellable: false,
      editable: false,
      cancellation: {
        cancelled_at: "2026-11-11T10:05:00Z",
        cancelled_by: OWNER_ID,
        reason: "Doublon",
      },
    });
    const { user, fake } = renderApp(
      SHEET,
      purchasingRoutes("owner", {
        [GET]: json(200, purchase({ cancellable: true })),
        [CANCEL]: json(200, cancelled),
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Annuler l'achat" }));
    const dialog = screen.getByRole("dialog", { name: "Annuler l'achat A-000012 ?" });
    await user.click(within(dialog).getByRole("button", { name: "Annuler l'achat" }));
    expect(within(dialog).getByText(REASON_REQUIRED)).toBeVisible();
    await user.type(within(dialog).getByLabelText("Motif"), "Doublon");
    await user.click(within(dialog).getByRole("button", { name: "Annuler l'achat" }));
    expect(
      await screen.findByText("Annulé le 11/11/2026 à 11 h 05 par vous — motif : Doublon", {
        normalizer: (t) => t.replace(/\s/g, " "),
      }),
    ).toBeVisible();
    expect(sent(fake.calls, "POST", "/cancel")).toEqual({ reason: "Doublon" });
    expect(screen.getByText("Annulé")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Corriger l'achat" })).toBeNull();
  });

  it("marchandise déjà sortie : message clair, rien ne change", async () => {
    const { user } = renderApp(
      SHEET,
      purchasingRoutes("owner", {
        [GET]: json(200, purchase({ cancellable: true })),
        [CANCEL]: apiError(422, "STOCK_ALREADY_LEFT", "Déjà sorti", { left: "3", requested: "20" }),
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Annuler l'achat" }));
    await user.type(screen.getByLabelText("Motif"), "Erreur");
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Annuler l'achat" }),
    );
    expect(await screen.findByText(STOCK_LEFT_MESSAGE)).toBeVisible();
    expect(screen.getByText("À payer")).toBeVisible();
  });
});
