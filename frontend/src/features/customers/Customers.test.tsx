import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  customer,
  customerSale,
  customerSheet,
  memberSession,
  preloadLot1Screens,
  route,
  SHOP_PATH,
} from "../../testing/lot1Screens";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";

beforeAll(preloadLot1Screens);

const PATH = `${SHOP_PATH}/clients`;
const LIST = route("GET", "/customers");
const SHEET = route("GET", "/customers/cust-moussa");
/** Texte sans aucun espace (montant et devise sont dans des éléments distincts). */
const compact = (text: string | null | undefined) => plain(text ?? "").replace(/\s/g, "");
const CANCELLED = customerSale({
  id: "sale-7",
  number: "V-000007",
  status: "cancelled",
  remaining: 0,
});
const GARBA = customer({
  id: "cust-garba",
  name: "Garba Issa",
  phone: "+237690000002",
  city: null,
});

describe("Clients (UC-VEN-11, CUS-01)", () => {
  it("liste puis recherche par nom ou téléphone (serveur) ; axe", async () => {
    const { user, container } = renderApp(PATH, {
      ...memberSession("owner"),
      [LIST]: json(200, { items: [customer(), GARBA] }),
      [route("GET", "/customers?q=690000002")]: json(200, { items: [GARBA] }),
    });
    const list = await screen.findByRole("list", { name: "Liste des clients" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(list.textContent).toContain("+237690000001 · Garoua");
    expect(await axeViolations(container)).toEqual([]);
    await user.type(screen.getByLabelText("Rechercher un client"), "690000002");
    expect(await screen.findByText("Garba Issa")).toBeVisible();
    expect(screen.queryByText("Moussa Hamadou")).toBeNull();
  });

  it("fiche : total acheté, total dû, ventes ; « Relevé des créances » ouvre Créances", async () => {
    const { user, router, container } = renderApp(`${PATH}?id=cust-moussa`, {
      ...memberSession("owner"),
      [SHEET]: json(200, customerSheet({ sales: [customerSale(), CANCELLED] })),
      [route("GET", "/customers/cust-moussa/statement")]: apiError(404, "NOT_FOUND", "x"),
    });
    expect(await screen.findByRole("heading", { name: "Moussa Hamadou" })).toBeVisible();
    const kpi = (label: string) => compact(screen.getByText(label).parentElement?.textContent);
    expect(kpi("Total acheté")).toContain(compact(money(1000000)));
    expect(kpi("Total dû")).toContain(compact(money(600000)));
    const sales = within(screen.getByRole("list", { name: "Ventes de Moussa Hamadou" }));
    const [credit, cancelled] = sales.getAllByRole("listitem");
    expect(credit?.textContent).toContain("V-000124");
    expect(credit && within(credit).getByText(`Reste ${money(600000)}`)).toBeVisible();
    expect(cancelled && within(cancelled).getByText("Annulée")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Relevé des créances" }));
    expect(router.state.location.pathname).toBe(`${SHOP_PATH}/creances`);
    expect(router.state.location.search).toBe("?vue=releve&client=cust-moussa");
  });

  it("nouveau client : nom et téléphone obligatoires, POST avec un identifiant v7", async () => {
    const created = customer({ id: "cust-new", name: "Aïcha Bouba", phone: "+237690000009" });
    const { user, fake, router } = renderApp(`${PATH}?vue=nouveau`, {
      ...memberSession("owner"),
      [route("POST", "/customers")]: json(201, created),
      [route("GET", "/customers/cust-new")]: json(200, customerSheet({ customer: created })),
    });
    await user.click(await screen.findByRole("button", { name: "Enregistrer le client" }));
    expect(screen.getByText("Le nom du client est vide")).toBeVisible();
    expect(fake.count(route("POST", "/customers"))).toBe(0);
    await user.type(screen.getByLabelText(/Nom du client/), "Aïcha Bouba");
    await user.type(screen.getByLabelText(/Téléphone/), "690000009");
    await user.click(screen.getByRole("radio", { name: "Entreprise" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer le client" }));
    expect(await screen.findByRole("heading", { name: "Aïcha Bouba" })).toBeVisible();
    expect(router.state.location.search).toBe("?id=cust-new");
    const sent = fake.calls.find((c) => c.method === "POST" && c.url.endsWith("/customers"))
      ?.body as Record<string, unknown>;
    expect(sent).toMatchObject({ name: "Aïcha Bouba", phone: "690000009", kind: "company" });
    expect(isUuidV7(String(sent["id"]))).toBe(true);
  });

  it("modifier : PATCH des seuls champs changés avec la version ; téléphone pris → message", async () => {
    const { user, fake } = renderApp(`${PATH}?vue=modifier&id=cust-moussa`, {
      ...memberSession("owner"),
      [SHEET]: json(200, customerSheet()),
      [route("PATCH", "/customers/cust-moussa")]: [
        apiError(409, "DUPLICATE", "Téléphone déjà pris"),
        json(200, customer({ city: "Maroua", version: 4 })),
      ],
    });
    const city = await screen.findByLabelText("Ville");
    await user.clear(city);
    await user.type(city, "Maroua");
    await user.click(screen.getByRole("button", { name: "Enregistrer les changements" }));
    expect(await screen.findByText(/appartient déjà à un client/)).toBeVisible();
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({
      version: 3,
      city: "Maroua",
    });
    await user.click(screen.getByRole("button", { name: "Enregistrer les changements" }));
    expect(await screen.findByRole("heading", { name: "Moussa Hamadou" })).toBeVisible();
  });

  it("vendeur : « Clients » n'est pas dans son menu (page introuvable)", async () => {
    renderApp(PATH, memberSession("seller"));
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });
});
