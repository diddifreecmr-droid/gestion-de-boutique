import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../../testing/axe";
import { apiError, json, type Call } from "../../../testing/fakeApi";
import { renderApp } from "../../../testing/renderApp";
import {
  preloadSettings,
  route,
  settings,
  settingsRoutes,
  viewPath,
} from "../../../testing/shopSettingsApi";
import { EMPLOYEE_EXCHANGE_HINT } from "./ExchangeSettingsSection";
import { APPROVAL_HINT } from "./SalesRulesSection";

const PATH = viewPath("boutique");
const PATCH = route("PATCH", "/settings");

beforeAll(preloadSettings);
beforeEach(() => {
  window.localStorage.clear();
});

const patches = (calls: readonly Call[]) =>
  calls.filter((c) => `${c.method} ${c.url}` === PATCH).map((c) => c.body);

const section = (title: string) => within(screen.getByRole("region", { name: title }));

const open = async (replies: Response[] = []) => {
  const view = renderApp(PATH, { ...settingsRoutes("owner"), [PATCH]: replies });
  await screen.findByRole("region", { name: "Prix et stock" });
  return view;
};

describe("Réglages de la boutique (UC-SOC-06, § 15.1)", () => {
  it("accord sous le prix minimum : « Non » par défaut ; « Oui » n'envoie que ce champ ; axe", async () => {
    const { user, fake, container } = await open([
      json(200, settings({ min_price_requires_approval: true, version: 4 })),
    ]);
    const prices = section("Prix et stock");
    const approval = prices.getByRole("radiogroup", {
      name: "Accord du propriétaire sous le prix minimum",
    });
    expect(within(approval).getByRole("radio", { name: "Non" })).toBeChecked();
    expect(prices.getByText(APPROVAL_HINT)).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(prices.getByRole("button", { name: /^Enregistrer/ }));
    expect(prices.getByText("Aucun changement à enregistrer.")).toBeVisible();
    expect(patches(fake.calls)).toEqual([]);

    await user.click(within(approval).getByRole("radio", { name: "Oui" }));
    await user.click(prices.getByRole("button", { name: /^Enregistrer/ }));
    expect(await screen.findByText("Prix et stock : enregistré.")).toBeVisible();
    expect(patches(fake.calls)).toEqual([{ min_price_requires_approval: true, version: 3 }]);
  });

  it("seuil de stock vérifié avant l'envoi ; la virgule est acceptée", async () => {
    const { user, fake } = await open([
      json(200, settings({ low_stock_threshold: "2.5", version: 4 })),
    ]);
    const prices = section("Prix et stock");
    const threshold = prices.getByLabelText(/Seuil de stock bas/);
    expect(threshold).toHaveValue("2");
    expect(prices.queryByLabelText(/Délai d'échange/)).toBeNull();
    await user.clear(threshold);
    await user.type(threshold, "2,55");
    await user.click(prices.getByRole("button", { name: /^Enregistrer/ }));
    expect(prices.getByText(/au dixième près/)).toBeVisible();
    expect(patches(fake.calls)).toEqual([]);

    await user.clear(threshold);
    await user.type(threshold, "2,5");
    await user.click(prices.getByRole("button", { name: /^Enregistrer/ }));
    expect(await screen.findByText("Prix et stock : enregistré.")).toBeVisible();
    expect(patches(fake.calls)).toEqual([{ low_stock_threshold: "2.5", version: 3 }]);
  });

  it("échanges (QC-4) : délai vérifié, employé « Désactivé » par défaut ; axe", async () => {
    const { user, fake, container } = await open([
      json(200, settings({ exchange_days: 7, employee_exchange_allowed: true, version: 4 })),
    ]);
    const exchanges = section("Échanges");
    const allowed = exchanges.getByRole("switch", { name: "L'employé peut faire des échanges" });
    expect(allowed).toHaveAttribute("aria-checked", "false");
    expect(allowed).toHaveAccessibleDescription(EMPLOYEE_EXCHANGE_HINT);
    expect(await axeViolations(container)).toEqual([]);
    await user.type(exchanges.getByLabelText(/Délai d'échange/), "999");
    await user.click(exchanges.getByRole("button", { name: /^Enregistrer/ }));
    expect(exchanges.getByText("Un nombre entier de 0 à 365, ou vide")).toBeVisible();
    expect(patches(fake.calls)).toEqual([]);

    await user.clear(exchanges.getByLabelText(/Délai d'échange/));
    await user.type(exchanges.getByLabelText(/Délai d'échange/), "7");
    await user.click(allowed);
    expect(allowed).toHaveAttribute("aria-checked", "true");
    await user.click(exchanges.getByRole("button", { name: /^Enregistrer/ }));
    expect(await screen.findByText("Échanges : enregistré.")).toBeVisible();
    expect(patches(fake.calls)).toEqual([
      { exchange_days: 7, employee_exchange_allowed: true, version: 3 },
    ]);
  });

  it("reçu puis en-tête : la version renvoyée sert à l'envoi suivant", async () => {
    const { user, fake } = await open([
      json(200, settings({ receipt_format: "58mm", copies: 2, version: 4 })),
      json(200, settings({ receipt_format: "58mm", copies: 2, version: 5 })),
    ]);
    const receipt = section("Reçu");
    await user.click(receipt.getByRole("radio", { name: "Ticket 58 mm" }));
    await user.click(receipt.getByRole("radio", { name: "2 exemplaires" }));
    await user.type(receipt.getByLabelText(/Message en bas du reçu/), "Merci !");
    await user.click(receipt.getByRole("button", { name: /^Enregistrer/ }));
    expect(await screen.findByText("Reçu : enregistré.")).toBeVisible();

    const header = section("En-tête du reçu");
    expect(header.getByText("Motos Garoua")).toBeVisible();
    await user.type(header.getByLabelText("NIU (facultatif)"), "M0123");
    await user.click(header.getByRole("button", { name: /^Enregistrer/ }));
    expect(await screen.findByText("En-tête du reçu : enregistré.")).toBeVisible();
    expect(patches(fake.calls)).toEqual([
      { receipt_format: "58mm", copies: 2, footer_message: "Merci !", version: 3 },
      { niu: "M0123", version: 4 },
    ]);
  });

  it("réception des achats et conflit de version expliqué", async () => {
    const { user, fake } = await open([apiError(409, "VERSION_CONFLICT", "x")]);
    const reception = section("Réception des achats");
    await user.click(reception.getByRole("radio", { name: "Ngaoundéré" }));
    await user.click(reception.getByRole("button", { name: /^Enregistrer/ }));
    expect(await reception.findByText(/modifié cet élément entre-temps/)).toBeVisible();
    expect(patches(fake.calls)).toEqual([{ reception_location_id: "loc-ngaoundere", version: 3 }]);
  });
});
