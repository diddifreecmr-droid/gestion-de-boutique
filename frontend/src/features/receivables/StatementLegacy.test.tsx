import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { setClock } from "../../testing/expensesApi";
import { json } from "../../testing/fakeApi";
import {
  CUSTOMER_ID,
  DETAIL_PATH,
  GET_ONE,
  NOW,
  preloadReceivables,
  receivable,
  receivableRoutes,
  RECEIVABLES_PATH,
  route,
  SELLER_ID,
} from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";

const STATEMENT = route("GET", `/customers/${CUSTOMER_ID}/statement`);
const line = (kind: string, amount: number, balance: number, extra = {}) => ({
  kind,
  on: "2026-10-01",
  receivable_id: "sale-124",
  number: null,
  amount,
  cancelled: false,
  balance_after: balance,
  ...extra,
});

beforeAll(preloadReceivables);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

describe("Relevé client (UC-CRE-05)", () => {
  it("chronologie vente / acompte / versements avec le reste après chaque opération", async () => {
    const { user, container } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("seller"),
      [GET_ONE]: json(200, receivable()),
      [STATEMENT]: json(200, {
        customer: { id: CUSTOMER_ID, name: "Moussa Hamadou", phone: "+237690000001" },
        total_due: 600000,
        lines: [
          line("sale", 1000000, 1000000, { number: "V-000124" }),
          line("deposit", 200000, 800000),
          line("installment", 50000, 800000, { number: "R-000000", cancelled: true }),
          line("installment", 200000, 600000, { number: "R-000001", on: "2026-11-01" }),
        ],
      }),
    });
    await screen.findByRole("heading", { name: "Créance de Moussa Hamadou" });
    await user.click(screen.getByRole("button", { name: "Relevé du client" }));
    expect(await screen.findByRole("heading", { name: "Relevé de Moussa Hamadou" })).toBeVisible();
    expect(plain(screen.getByText("Total dû").nextElementSibling?.textContent ?? "")).toBe(
      money(600000),
    );
    const items = within(screen.getByRole("list", { name: "Opérations du client" })).getAllByRole(
      "listitem",
    );
    expect(items.map((item) => plain(item.textContent))).toEqual([
      `Vente à crédit V-000124+ ${money(1000000)}01/10/2026Reste après : ${money(1000000)}`,
      `Acompte− ${money(200000)}01/10/2026Reste après : ${money(800000)}`,
      `Versement R-000000− ${money(50000)}01/10/2026Annulé`,
      `Versement R-000001− ${money(200000)}01/11/2026Reste après : ${money(600000)}`,
    ]);
    expect(within(items[2] ?? container).getByText(/Versement R-000000/)).toHaveClass(
      "line-through",
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("client sans opération à crédit", async () => {
    renderApp(`${RECEIVABLES_PATH}?vue=releve&client=${CUSTOMER_ID}`, {
      ...receivableRoutes("owner"),
      [STATEMENT]: json(200, {
        customer: { id: CUSTOMER_ID, name: "Moussa Hamadou", phone: "+237690000001" },
        total_due: 0,
        lines: [],
      }),
    });
    expect(await screen.findByText("Aucune opération à crédit.")).toBeVisible();
  });
});

describe("Créance ancienne (UC-CRE-02, propriétaire)", () => {
  it("nouveau client, montant, date d'origine, description, vendeur : puis ouvre la fiche", async () => {
    const POST = route("POST", "/receivables");
    const created = receivable({
      id: "rec-old",
      origin: "legacy",
      sale_number: null,
      description: "1 moto Haojue, cahier 2026",
    });
    const { user, fake, router, container } = renderApp(RECEIVABLES_PATH, {
      ...receivableRoutes("owner"),
      [POST]: json(201, created),
      [route("GET", "/receivables/rec-old")]: json(200, created),
    });
    await user.click(await screen.findByRole("button", { name: "Créance ancienne" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer la créance" }));
    expect(screen.getByText("Choisissez ou créez le client")).toBeVisible();
    expect(screen.getByText("La description est vide")).toBeVisible();
    expect(fake.count(POST)).toBe(0);
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Nouveau client" }));
    await user.type(screen.getByLabelText("Nom du client"), "Garba Issa");
    await user.type(screen.getByLabelText("Téléphone du client"), "690000002");
    await user.type(screen.getByLabelText("Montant dû aujourd'hui"), "300000");
    await user.type(screen.getByLabelText("Date d'origine"), "2026-03-15");
    await user.type(screen.getByLabelText("Description"), "1 moto Haojue, cahier 2026");
    await user.click(screen.getByRole("radio", { name: "Ibrahim Sali" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer la créance" }));
    expect(await screen.findByText("Créance ancienne de Moussa Hamadou enregistrée")).toBeVisible();
    expect(router.state.location.search).toBe("?vue=fiche&id=rec-old");
    const body = fake.calls.find((c) => `${c.method} ${c.url}` === POST)?.body as { id: string };
    expect(body).toEqual({
      id: body.id,
      customer: { id: null, name: "Garba Issa", phone: "+237690000002", kind: "individual" },
      amount: 300000,
      opened_on: "2026-03-15",
      description: "1 moto Haojue, cahier 2026",
      responsible_seller_id: SELLER_ID,
      terms: null,
    });
  });

  it("vendeur : l'adresse de la créance ancienne ramène à la liste", async () => {
    renderApp(`${RECEIVABLES_PATH}?vue=ancienne`, receivableRoutes("seller"));
    expect(await screen.findByRole("list", { name: "Liste des créances" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Créance ancienne" })).toBeNull();
  });
});
