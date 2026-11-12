import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  alert,
  alertPage,
  memberSession,
  preloadLot1Screens,
  route,
  SHOP_PATH,
} from "../../testing/lot1Screens";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadLot1Screens);

const PATH = `${SHOP_PATH}/alertes`;
const UNREAD = route("GET", "/alerts?unread_only=true");
const ALL = route("GET", "/alerts");
const SALE_ALERT = alert({
  id: "alert-2",
  type: "entry_refused",
  entity: { type: "sale", id: "sale-9", number: "V-000009" },
  message: "Saisie refusée : V-000009 sous le prix minimum",
});

const rows = async () =>
  within(await screen.findByRole("list", { name: "Liste des alertes" })).getAllByRole("listitem");

describe("Alertes (UC-SOC-09)", () => {
  it("non lues d'abord : type, message, date, compteur ; aucune violation axe", async () => {
    const { container } = renderApp(PATH, {
      ...memberSession("seller"),
      [UNREAD]: json(200, alertPage([alert(), SALE_ALERT])),
    });
    const [first, second] = await rows();
    if (first === undefined || second === undefined) throw new Error("deux alertes attendues");
    expect(within(first).getByText("Stock bas")).toBeVisible();
    expect(within(first).getByText("Nouvelle")).toBeVisible();
    expect(first.textContent).toContain("1 restant à Garoua");
    expect(first.textContent).toContain("11/11/2026");
    expect(within(second).getByText("Saisie refusée")).toBeVisible();
    expect(screen.getByText("2 alertes non lues")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("« Marquer traitée » : POST /read, la pastille disparaît, le compteur baisse (ALR-01)", async () => {
    const { user, fake } = renderApp(PATH, {
      ...memberSession("seller"),
      [UNREAD]: json(200, alertPage([alert(), SALE_ALERT])),
      [route("POST", "/alerts/alert-1/read")]: json(200, { unread_count: 1 }),
    });
    const [first] = await rows();
    if (first === undefined) throw new Error("alerte attendue");
    await user.click(within(first).getByRole("button", { name: "Marquer traitée" }));
    expect(await screen.findByText("1 alerte non lue")).toBeVisible();
    expect(within(first).queryByText("Nouvelle")).toBeNull();
    expect(within(first).queryByRole("button", { name: "Marquer traitée" })).toBeNull();
    expect(fake.count(route("POST", "/alerts/alert-1/read"))).toBe(1);
  });

  it("« Ouvrir » : marque traitée puis ouvre l'élément lié dans l'écran du rôle (ALR-02)", async () => {
    const { user, router } = renderApp(PATH, {
      ...memberSession("seller"),
      [UNREAD]: json(200, alertPage([SALE_ALERT])),
      [route("POST", "/alerts/alert-2/read")]: json(200, { unread_count: 0 }),
      [route("GET", "/sales/sale-9")]: apiError(404, "NOT_FOUND", "absente"),
    });
    const [row] = await rows();
    if (row === undefined) throw new Error("alerte attendue");
    await user.click(within(row).getByRole("button", { name: "Ouvrir" }));
    await screen.findByRole("heading", { level: 1 });
    expect(router.state.location.pathname).toBe(`${SHOP_PATH}/mes-ventes`);
    expect(router.state.location.search).toBe("?id=sale-9");
  });

  it("comptable : une alerte de vente n'offre aucun lien (écran interdit à son rôle)", async () => {
    renderApp(PATH, {
      ...memberSession("accountant"),
      [UNREAD]: json(200, alertPage([SALE_ALERT])),
    });
    const [row] = await rows();
    if (row === undefined) throw new Error("alerte attendue");
    expect(within(row).queryByRole("button", { name: "Ouvrir" })).toBeNull();
    expect(within(row).getByRole("button", { name: "Marquer traitée" })).toBeVisible();
  });

  it("« Toutes » : lues en gris, « Résolue » si la cause a disparu ; « Voir plus » suit le curseur", async () => {
    const { user } = renderApp(PATH, {
      ...memberSession("owner"),
      [UNREAD]: json(200, alertPage([])),
      [ALL]: json(200, alertPage([alert({ read: true, active: false })], "c2")),
      [route("GET", "/alerts?cursor=c2")]: json(200, alertPage([SALE_ALERT])),
    });
    expect(await screen.findByText("Aucune alerte à traiter.")).toBeVisible();
    await user.click(screen.getByRole("radio", { name: "Toutes" }));
    const [read] = await rows();
    if (read === undefined) throw new Error("alerte attendue");
    expect(within(read).getByText("Résolue")).toBeVisible();
    expect(within(read).queryByText("Nouvelle")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Voir plus" }));
    expect(await screen.findByText("Saisie refusée")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Voir plus" })).toBeNull();
  });

  it("alerte d'un autre (404, ALR-03) : message clair et liste relue", async () => {
    const { user, fake } = renderApp(PATH, {
      ...memberSession("seller"),
      [UNREAD]: json(200, alertPage([alert()])),
      [route("POST", "/alerts/alert-1/read")]: apiError(404, "NOT_FOUND", "Alerte introuvable"),
    });
    const [row] = await rows();
    if (row === undefined) throw new Error("alerte attendue");
    await user.click(within(row).getByRole("button", { name: "Marquer traitée" }));
    expect(await screen.findByText(/Cette alerte n'existe plus pour vous/)).toBeVisible();
    expect(fake.count(UNREAD)).toBe(2);
  });

  it("hors connexion : « Connexion nécessaire » et « Réessayer »", async () => {
    renderApp(PATH, { ...memberSession("driver"), [UNREAD]: new TypeError("Failed to fetch") });
    expect(
      await screen.findByText("Connexion nécessaire pour afficher les alertes."),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeVisible();
  });
});
