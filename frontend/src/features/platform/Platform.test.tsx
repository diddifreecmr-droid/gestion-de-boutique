import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  ADMIN_SHOP_ID,
  adminSession,
  memberSession,
  PLATFORM,
  preloadLot1Screens,
  shopAccess,
  shopSummary,
} from "../../testing/lot1Screens";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadLot1Screens);

const ONE = `${PLATFORM}/${ADMIN_SHOP_ID}`;
const SHEET_PATH = `/plateforme?id=${ADMIN_SHOP_ID}`;
const sheetRoutes = (access = shopAccess()) => ({
  ...adminSession(),
  [`GET ${ONE}`]: json(200, shopSummary()),
  [`GET ${ONE}/access`]: json(200, access),
});

describe("Console plateforme (TR-23, UC-SOC-01)", () => {
  it("liste des boutiques : nom, ville, compte, statut ; axe", async () => {
    const { container } = renderApp("/plateforme", {
      ...adminSession([
        shopSummary(),
        shopSummary({ shop_id: "s-2", name: "Motos Maroua", city: "Maroua", status: "closed" }),
      ]),
    });
    const list = await screen.findByRole("list", { name: "Liste des boutiques" });
    const [open, closed] = within(list).getAllByRole("listitem");
    expect(open?.textContent).toContain("Garoua · Moussa · depuis le 01/11/2026");
    expect(closed && within(closed).getByText("Fermée")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Mon compte" })).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("ouvrir une boutique : champs obligatoires, POST, code provisoire montré une seule fois", async () => {
    const { user, fake } = renderApp("/plateforme?vue=nouvelle", {
      ...adminSession(),
      [`POST ${PLATFORM}`]: json(201, {
        shop: shopSummary({ name: "Motos Ngaoundéré" }),
        owner_id: "u-9",
        owner_created: true,
        temporary_pin: "482915",
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Ouvrir la boutique" }));
    expect(screen.getByText("Nom de la boutique : obligatoire")).toBeVisible();
    expect(screen.getByText("Type de boutique : à choisir")).toBeVisible();
    expect(fake.count(`POST ${PLATFORM}`)).toBe(0);
    await user.click(screen.getByRole("radio", { name: "Motos et camions" }));
    await user.type(screen.getByLabelText(/Nom de la boutique/), "Motos Ngaoundéré");
    await user.type(screen.getByLabelText(/^Ville/), "Ngaoundéré");
    await user.type(screen.getByLabelText(/Téléphone de la boutique/), "222000000");
    await user.type(screen.getByLabelText(/Nom du propriétaire/), "Hamidou");
    await user.type(screen.getByLabelText(/Téléphone du propriétaire/), "690000077");
    await user.click(screen.getByRole("button", { name: "Ouvrir la boutique" }));
    expect(await screen.findByText("482915")).toBeVisible();
    expect(screen.getByText(/Code provisoire du propriétaire \(690000077\)/)).toBeVisible();
    expect(
      fake.calls.find((c) => c.url.endsWith("/platform/shops") && c.method === "POST")?.body,
    ).toEqual({
      profile_code: "motos",
      name: "Motos Ngaoundéré",
      city: "Ngaoundéré",
      phone: "222000000",
      address: null,
      owner: { name: "Hamidou", phone: "690000077" },
    });
    await user.click(screen.getByRole("button", { name: /J'ai noté le code/ }));
    expect(await screen.findByRole("list", { name: "Liste des boutiques" })).toBeVisible();
    expect(screen.queryByText("482915")).toBeNull();
    expect(window.location.search).not.toContain("482915");
  });

  it("fiche : droits d'offre en vigueur, délégation absente ; activer la saisie hors connexion", async () => {
    const { user, fake, container } = renderApp(SHEET_PATH, {
      ...sheetRoutes(),
      [`PATCH ${ONE}`]: json(200, shopSummary()),
    });
    expect(await screen.findByRole("heading", { name: "Motos Garoua" })).toBeVisible();
    expect(screen.getByText("Inactif")).toBeVisible();
    expect(screen.getByRole("radio", { name: "Selon l'offre" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByText(/Seul le propriétaire peut vous ouvrir sa boutique/)).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("radio", { name: "Activé" }));
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({
      entitlements: { offline_capture: true },
    });
    expect(fake.count(`GET ${ONE}/access`)).toBe(2); // relu après le changement
  });

  it("délégation en cours : fin affichée ; fermer la boutique demande confirmation", async () => {
    const { user, fake } = renderApp(SHEET_PATH, {
      ...sheetRoutes(shopAccess({ admin_access_until: "2026-11-12T09:00:00Z" })),
      [`PATCH ${ONE}`]: json(200, shopSummary({ status: "closed" })),
    });
    expect(await screen.findByText(/jusqu'au 12\/11\/2026 à 10/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Fermer la boutique" }));
    expect(fake.count(`PATCH ${ONE}`)).toBe(0);
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Fermer" }));
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({ status: "closed" });
  });

  it("refus du serveur : message lisible, la fiche reste", async () => {
    const { user } = renderApp(SHEET_PATH, {
      ...sheetRoutes(),
      [`PATCH ${ONE}`]: apiError(400, "VALIDATION_ERROR", "Saisie invalide", { fields: ["x"] }),
    });
    await user.click(await screen.findByRole("radio", { name: "Désactivé" }));
    expect(await screen.findByText(/Vérifiez la saisie/)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Motos Garoua" })).toBeVisible();
  });

  it("un membre de boutique n'a pas de console (page introuvable)", async () => {
    renderApp("/plateforme", memberSession("owner"));
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });
});
