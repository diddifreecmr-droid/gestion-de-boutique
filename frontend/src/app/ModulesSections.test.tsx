/**
 * Sections et liens d'un module éteint (décision client du 12/11/2026) : créances de la fiche
 * client, liens des alertes, réception des achats dans les réglages, messages MODULE_DISABLED.
 */
import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { ApiError } from "../core/api/errors";
import { saleErrorMessage } from "../features/sales/saleErrorMessage";
import { json } from "../testing/fakeApi";
import {
  alert,
  alertPage,
  customerSale,
  customerSheet,
  memberSession,
  preloadLot1Screens,
  route,
  SHOP_PATH,
} from "../testing/lot1Screens";
import { MINIMAL, PROFILE_ROUTE, without } from "../testing/modules";
import { renderApp } from "../testing/renderApp";
import {
  preloadSettings,
  profileWithRoles,
  settingsRoutes,
  viewPath,
} from "../testing/shopSettingsApi";

beforeAll(async () => {
  await Promise.all([preloadLot1Screens(), preloadSettings()]);
});

const SHEET = route("GET", "/customers/cust-moussa");
const UNREAD = route("GET", "/alerts?unread_only=true");
const RECEIVABLE_ALERT = alert({
  id: "alert-3",
  type: "receivable_reminder",
  entity: { type: "receivable", id: "rec-1", number: "V-000124" },
  message: "Rappel : créance V-000124",
});

function withModules(modules: readonly string[]) {
  return { [PROFILE_ROUTE]: json(200, { ...profileWithRoles(), enabled_modules: modules }) };
}

describe("fiche client", () => {
  const open = (modules: readonly string[]) =>
    renderApp(`${SHOP_PATH}/clients?id=cust-moussa`, {
      ...memberSession("owner"),
      ...withModules(modules),
      [SHEET]: json(200, customerSheet({ sales: [customerSale()] })),
    });

  it("sans Créances : ni total dû, ni reste, ni relevé des créances", async () => {
    open(without("receivables"));
    expect(await screen.findByRole("heading", { name: "Moussa Hamadou" })).toBeVisible();
    expect(screen.getByText("Total acheté")).toBeVisible();
    expect(screen.queryByText("Total dû")).toBeNull();
    expect(screen.queryByText(/^Reste/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Relevé des créances" })).toBeNull();
  });

  it("avec Créances : total dû et relevé (témoin)", async () => {
    open(MINIMAL.concat("receivables"));
    expect(await screen.findByText("Total dû")).toBeVisible();
    expect(screen.getByRole("button", { name: "Relevé des créances" })).toBeVisible();
  });
});

describe("alertes", () => {
  it("sans Créances : l'alerte d'une créance n'offre pas « Ouvrir »", async () => {
    renderApp(`${SHOP_PATH}/alertes`, {
      ...memberSession("owner"),
      ...withModules(MINIMAL),
      [UNREAD]: json(200, alertPage([RECEIVABLE_ALERT])),
    });
    const list = await screen.findByRole("list", { name: "Liste des alertes" });
    const [row] = within(list).getAllByRole("listitem");
    if (row === undefined) throw new Error("alerte attendue");
    expect(within(row).queryByRole("button", { name: "Ouvrir" })).toBeNull();
    expect(within(row).getByRole("button", { name: "Marquer traitée" })).toBeVisible();
  });

  it("avec Créances : « Ouvrir » est proposé (témoin)", async () => {
    renderApp(`${SHOP_PATH}/alertes`, {
      ...memberSession("owner"),
      ...withModules(MINIMAL.concat("receivables")),
      [UNREAD]: json(200, alertPage([RECEIVABLE_ALERT])),
    });
    expect(await screen.findByRole("button", { name: "Ouvrir" })).toBeVisible();
  });
});

describe("réglages de la boutique", () => {
  it.each([
    [without("purchases"), false],
    [MINIMAL.concat("purchases"), true],
  ])("réception des achats selon le module Achats (%#)", async (modules, shown) => {
    renderApp(viewPath("boutique"), { ...settingsRoutes("owner"), ...withModules(modules) });
    await screen.findByRole("region", { name: "Prix et stock" });
    expect(screen.queryByRole("region", { name: "Réception des achats" }) !== null).toBe(shown);
  });
});

describe("refus MODULE_DISABLED d'une action", () => {
  it("message clair dans les écrans de saisie", () => {
    const error = new ApiError(403, "MODULE_DISABLED", "Module désactivé");
    expect(saleErrorMessage(error, [], "Garoua")).toBe(
      "Cette fonction n'est pas activée pour cette boutique.",
    );
  });
});
