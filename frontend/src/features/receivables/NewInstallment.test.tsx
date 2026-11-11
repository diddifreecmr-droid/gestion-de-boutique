import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import type { InstallmentReceipt, Receivable } from "../../core/gateways/receivablesContract";
import { axeViolations } from "../../testing/axe";
import { setClock } from "../../testing/expensesApi";
import { apiError, json, SHOP_A } from "../../testing/fakeApi";
import {
  CUSTOMER,
  GET_ONE,
  installment,
  NOW,
  preloadReceivables,
  receivable,
  receivableRoutes,
  RECEIVABLE_ID,
  RECEIVABLES_PATH,
  route,
  SEARCH,
  TODAY,
} from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";

const PAY = route("POST", `/receivables/${RECEIVABLE_ID}/installments`);
function paid(amount: number, after: Receivable) {
  return {
    installment: installment({ id: "inst-2", number: "R-000002", amount }),
    receivable: after,
  };
}

const RECEIPT: InstallmentReceipt = {
  shop_name: "Motos Garoua",
  shop_city: "Garoua",
  shop_phone: "+237699000000",
  number: "R-000002",
  paid_on: TODAY,
  customer_name: "Moussa Hamadou",
  customer_phone: "+237690000001",
  amount: 600000,
  mode_name: "Espèces",
  reference: null,
  nature: "normal",
  cancelled: false,
  total_paid: 800000,
  remaining: 0,
  settled: true,
  sale_number: "V-000124",
};

let print: ReturnType<typeof vi.spyOn>;
beforeAll(preloadReceivables);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
  print = vi.spyOn(window, "print").mockImplementation(() => undefined);
});
afterEach(() => {
  vi.useRealTimers();
});

const amountField = () => screen.getByLabelText("Montant du versement");
const validate = () => screen.getByRole("button", { name: "Valider le versement" });
const afterText = () => plain(screen.getByText(/Reste à payer après ce versement/).textContent);

describe("Enregistrer un versement (UC-CRE-03)", () => {
  it("vendeur, depuis « Versement » de l'accueil : client, reste affiché, soldée, reçu « Soldé »", async () => {
    const settled = receivable({ total_paid: 800000, remaining: 0, status: "settled" });
    const { user, fake, router, container } = renderApp(`/s/${SHOP_A}`, {
      ...receivableRoutes("seller"),
      [SEARCH]: json(200, { items: [CUSTOMER] }),
      [PAY]: json(201, paid(600000, settled)),
      [route("GET", "/installments/inst-2/receipt")]: json(200, RECEIPT),
    });
    await user.click(await screen.findByRole("button", { name: "Versement" }));
    expect(router.state.location.pathname).toBe(RECEIVABLES_PATH);
    await user.click(await screen.findByLabelText("Chercher le client"));
    await user.paste("Moussa");
    await user.click(await screen.findByRole("button", { name: /Moussa Hamadou/ }));
    await screen.findByLabelText("Montant du versement");
    await user.type(amountField(), "200000");
    expect(afterText()).toBe(`Reste à payer après ce versement : ${money(400000)}`);
    await user.clear(amountField());
    await user.type(amountField(), "600000");
    expect(afterText()).toBe(`Reste à payer après ce versement : ${money(0)}`);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(validate());

    expect(
      await screen.findByRole("heading", { name: "Versement enregistré — reçu n° R-000002" }),
    ).toBeVisible();
    expect(screen.getByText("Soldée")).toBeVisible();
    const call = fake.calls.find((c) => `${c.method} ${c.url}` === PAY);
    const body = call?.body as { id: string };
    expect(isUuidV7(body.id)).toBe(true);
    expect(call?.body).toEqual({
      id: body.id,
      amount: 600000,
      mode_id: "mode-cash",
      paid_on: TODAY,
      reference: null,
    });
    expect(call?.headers.get("X-Captured-At")).toMatch(/^2026-11-11T/);
    expect(screen.getByRole("button", { name: "Partager" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "Imprimer le reçu" }));
    const receipt = await screen.findByRole("article", { name: "Reçu de versement" });
    expect(print).toHaveBeenCalledTimes(1);
    expect(receipt).toHaveClass("receipt", "receipt--thermal-80");
    expect(plain(receipt.textContent)).toContain("N° R-000002");
    expect(plain(receipt.textContent)).toContain(`Total déjà versé${money(800000)}`);
    expect(within(receipt).getByText("Soldé")).toHaveClass("receipt__mention");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Imprimer de nouveau" }));
    await vi.waitFor(() => {
      expect(print).toHaveBeenCalledTimes(2);
    });
    await user.click(screen.getByRole("button", { name: "Retour" }));
    await user.click(await screen.findByRole("button", { name: "Voir la créance" }));
    expect(router.state.location.search).toBe(`?vue=fiche&id=${RECEIVABLE_ID}`);
  });

  it("OVERPAYMENT : message avec le reste du serveur ; au-delà du reste connu, rien n'est envoyé", async () => {
    const { user, fake } = renderApp(`${RECEIVABLES_PATH}?vue=versement&id=${RECEIVABLE_ID}`, {
      ...receivableRoutes("owner"),
      [GET_ONE]: json(200, receivable()),
      [PAY]: apiError(422, "OVERPAYMENT", "Le versement dépasse le reste à payer", {
        remaining: 250000,
        amount: 300000,
      }),
    });
    await user.type(await screen.findByLabelText("Montant du versement"), "700000");
    expect(
      screen.getByText(`Le versement dépasse le reste à payer : il reste ${money(600000)}.`, {
        normalizer: plain,
      }),
    ).toBeVisible();
    await user.click(validate());
    expect(fake.count(PAY)).toBe(0);
    await user.clear(amountField());
    await user.type(amountField(), "300000");
    await user.click(validate());
    expect(
      await screen.findByText(
        `Le versement dépasse le reste à payer : il reste ${money(250000)}.`,
        {
          normalizer: plain,
        },
      ),
    ).toBeVisible();
  });

  it("référence obligatoire du mode, coupure réseau puis renvoi avec le même identifiant", async () => {
    const after = receivable({ total_paid: 300000, remaining: 500000 });
    const { user, fake } = renderApp(`${RECEIVABLES_PATH}?vue=versement&id=${RECEIVABLE_ID}`, {
      ...receivableRoutes("seller"),
      [GET_ONE]: json(200, receivable()),
      [PAY]: [new TypeError("Failed to fetch"), json(201, paid(100000, after))],
    });
    await user.type(await screen.findByLabelText("Montant du versement"), "100000");
    await user.click(screen.getByRole("radio", { name: "Orange Money" }));
    await user.click(validate());
    expect(screen.getByText("La référence est obligatoire pour Orange Money")).toBeVisible();
    expect(fake.count(PAY)).toBe(0);
    await user.type(screen.getByLabelText("Référence (facultatif)"), "OM-778");
    await user.click(validate());
    expect(await screen.findByText(/Connexion nécessaire : rien n'est enregistré/)).toBeVisible();
    await user.click(validate());
    await screen.findByRole("heading", { name: /reçu n° R-000002/ });
    const bodies = fake.calls.filter((c) => `${c.method} ${c.url}` === PAY).map((c) => c.body);
    expect(bodies).toHaveLength(2);
    expect(bodies[0]).toEqual(bodies[1]);
    expect(bodies[0]).toMatchObject({ mode_id: "mode-om", reference: "OM-778" });
  });
});
