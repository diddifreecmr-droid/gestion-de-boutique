/** Console : modules d'une boutique (décisions client des 12 et 13/11/2026, specs § 15.1). */
import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { apiError, json, type Reply } from "../../testing/fakeApi";
import {
  ADMIN_SHOP_ID,
  adminSession,
  PLATFORM,
  preloadLot1Screens,
  shopAccess,
  shopSummary,
} from "../../testing/lot1Screens";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadLot1Screens);

const ONE = `${PLATFORM}/${ADMIN_SHOP_ID}`;
const MINIMAL = ["audit", "catalog", "core", "sales"];

function openSheet(enabled: string[], patch: Reply | Reply[] = json(200, shopSummary())) {
  return renderApp(`/plateforme?id=${ADMIN_SHOP_ID}`, {
    ...adminSession(),
    [`GET ${ONE}`]: json(200, shopSummary({ enabled_modules: enabled })),
    [`GET ${ONE}/access`]: json(200, shopAccess()),
    [`PATCH ${ONE}`]: patch,
  });
}

const toggle = (name: string) => screen.getByRole("switch", { name });
const saveButton = () => screen.getByRole("button", { name: "Enregistrer les modules" });

describe("console — modules d'une boutique", () => {
  it("toujours actifs sur une ligne ; interrupteurs des modules construits ; axe", async () => {
    const { container } = openSheet(MINIMAL);
    expect(
      await screen.findByText("Toujours actifs : Socle, Journal, Catalogue et stock, Ventes"),
    ).toBeVisible();
    expect(screen.queryByRole("list", { name: "Modules toujours actifs" })).toBeNull();
    expect(screen.queryByText("Toujours actif")).toBeNull();
    const optional = screen.getByRole("group", { name: "Modules facultatifs" });
    expect(
      within(optional)
        .getAllByRole("switch")
        .map((s) => [s.getAttribute("aria-label"), s.getAttribute("aria-checked")]),
    ).toEqual([
      ["Achats", "false"],
      ["Créances", "false"],
      ["Dépenses", "false"],
      ["Tableau de bord", "false"],
    ]);
    expect(saveButton()).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Aucun changement à enregistrer.")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("désactiver Créances : ce qui disparaît est dit avant d'enregistrer, puis PATCH", async () => {
    const { user, fake, container } = openSheet([...MINIMAL, "receivables", "expenses"]);
    await user.click(await screen.findByRole("switch", { name: "Créances" }));
    expect(toggle("Créances")).toHaveAttribute("aria-checked", "false");
    expect(
      screen.getByText(
        "Créances désactivé : plus de vente à crédit, de versements ni de garants. Les données sont gardées.",
      ),
    ).toBeVisible();
    expect(fake.count(`PATCH ${ONE}`)).toBe(0);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(saveButton());
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({
      modules: ["core", "audit", "catalog", "sales", "expenses"],
    });
    expect(fake.count(`GET ${ONE}`)).toBe(2); // fiche relue après l'enregistrement
  });

  it("modules à venir : pastille « Bientôt », sans interrupteur ; axe", async () => {
    const { container } = openSheet(MINIMAL);
    const upcoming = await screen.findByRole("list", { name: "Modules à venir" });
    const rows = within(upcoming).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Transferts"),
      expect.stringContaining("Transport"),
      expect.stringContaining("Import Excel"),
    ]);
    expect(within(upcoming).getAllByText("Bientôt")).toHaveLength(3);
    expect(within(upcoming).queryByRole("switch")).toBeNull();
    expect(within(upcoming).queryByRole("button")).toBeNull();
    for (const name of ["Transferts", "Transport", "Import Excel"]) {
      expect(screen.queryByRole("switch", { name })).toBeNull();
    }
    expect(await axeViolations(container)).toEqual([]);
  });

  it("boutique lue avec un module à venir : jamais renvoyé au PATCH", async () => {
    const { user, fake } = openSheet([...MINIMAL, "transfers", "transport", "import"]);
    await user.click(await screen.findByRole("switch", { name: "Achats" }));
    await user.click(saveButton());
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({
      modules: ["core", "audit", "catalog", "sales", "purchases"],
    });
  });

  it("refus 422 MODULE_NOT_YET_AVAILABLE : message clair, la fiche reste", async () => {
    const { user } = openSheet(
      MINIMAL,
      apiError(422, "MODULE_NOT_YET_AVAILABLE", "Pas encore disponible", { module: "import" }),
    );
    await user.click(await screen.findByRole("switch", { name: "Achats" }));
    await user.click(saveButton());
    expect(
      await screen.findByText(
        "Le module « Import Excel » n'est pas encore disponible : il ne peut pas être activé. Rien n'a été enregistré.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Motos Garoua" })).toBeVisible();
  });

  it("fiche d'une boutique : pas de bloc « Mon compte » répété en bas", async () => {
    openSheet(MINIMAL);
    expect(await screen.findByRole("heading", { name: "Motos Garoua" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Mon compte" })).toBeNull();
  });

  it("conflit de version : message clair et fiche relue", async () => {
    const { user, fake } = openSheet(
      MINIMAL,
      apiError(409, "VERSION_CONFLICT", "Boutique modifiée entre-temps"),
    );
    await user.click(await screen.findByRole("switch", { name: "Achats" }));
    await user.click(saveButton());
    expect(await screen.findByText(/La boutique a été modifiée entre-temps/)).toBeVisible();
    expect(fake.count(`GET ${ONE}`)).toBe(2);
  });

  it("refus 422 du serveur : message lisible, la fiche reste", async () => {
    const { user } = openSheet(
      MINIMAL,
      apiError(422, "MODULE_DEPENDENCY", "Transport a besoin de Transferts", {
        module: "transport",
        requires: "transfers",
      }),
    );
    await user.click(await screen.findByRole("switch", { name: "Dépenses" }));
    await user.click(saveButton());
    expect(
      await screen.findByText(
        "Le module « Transport » a besoin du module « Transferts » : activez-le aussi, ou désactivez « Transport ». Rien n'a été enregistré.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Motos Garoua" })).toBeVisible();
  });
});
