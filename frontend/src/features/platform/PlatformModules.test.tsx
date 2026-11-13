/** Console : modules d'une boutique (décision client du 12/11/2026, specs § 15.1). */
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
  it("socle, journal, catalogue, ventes : toujours actifs, sans interrupteur ; axe", async () => {
    const { container } = openSheet(MINIMAL);
    const always = await screen.findByRole("list", { name: "Modules toujours actifs" });
    const rows = within(always).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Socle"),
      expect.stringContaining("Journal d'actions"),
      expect.stringContaining("Catalogue et stock"),
      expect.stringContaining("Ventes et reçus"),
    ]);
    expect(within(always).getAllByText("Toujours actif")).toHaveLength(4);
    expect(within(always).queryByRole("switch")).toBeNull();
    const optional = screen.getByRole("group", { name: "Modules facultatifs" });
    expect(
      within(optional)
        .getAllByRole("switch")
        .map((s) => [s.getAttribute("aria-label"), s.getAttribute("aria-checked")]),
    ).toEqual([
      ["Achats", "false"],
      ["Créances", "false"],
      ["Dépenses", "false"],
      ["Transferts", "false"],
      ["Transport", "false"],
      ["Tableau de bord", "false"],
      ["Import Excel", "false"],
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

  it("dépendance : Transport active Transferts ; désactiver Transferts désactive Transport", async () => {
    const { user, fake } = openSheet(MINIMAL);
    await screen.findByRole("switch", { name: "Transport" });
    expect(toggle("Transport")).toHaveAccessibleDescription(
      "A besoin de Transferts : l'activer active aussi Transferts.",
    );
    expect(toggle("Transferts")).toHaveAccessibleDescription(
      "Le désactiver désactive aussi Transport.",
    );
    await user.click(toggle("Transport"));
    expect(toggle("Transferts")).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText(/^Transport activé/)).toBeVisible();
    expect(screen.getByText(/^Transferts activé/)).toBeVisible();
    await user.click(toggle("Transferts"));
    expect(toggle("Transport")).toHaveAttribute("aria-checked", "false");
    expect(saveButton()).toHaveAttribute("aria-disabled", "true"); // retour à l'état lu

    await user.click(toggle("Transport"));
    await user.click(saveButton());
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({
      modules: ["core", "audit", "catalog", "sales", "transfers", "transport"],
    });
  });

  it("depuis une boutique avec Transport, désactiver Transferts annonce les deux pertes", async () => {
    const { user } = openSheet([...MINIMAL, "transfers", "transport"]);
    await user.click(await screen.findByRole("switch", { name: "Transferts" }));
    expect(screen.getByText(/^Transferts désactivé : plus de déplacements/)).toBeVisible();
    expect(screen.getByText(/^Transport désactivé : plus de camions/)).toBeVisible();
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
      apiError(422, "MODULE_DEPENDENCY", "Transport a besoin de Transferts"),
    );
    await user.click(await screen.findByRole("switch", { name: "Dépenses" }));
    await user.click(saveButton());
    expect(
      await screen.findByText("Refusé par le serveur : Transport a besoin de Transferts."),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Motos Garoua" })).toBeVisible();
  });
});
