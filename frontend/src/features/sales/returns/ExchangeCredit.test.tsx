/** Échange à crédit (décision client specs § 15.1) : client d'origine, acompte, reste dû. */
import { screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { RecordSaleCommand } from "../../../core/gateways/salesContract";
import type { SaleReturnCommand } from "../../../core/gateways/returnsContract";
import { axeViolations } from "../../../testing/axe";
import { articleButton, money, plain, preloadSales } from "../../../testing/renderSale";
import { NOW } from "../../../testing/salesFixtures";
import { ONE_SANYA, openReturn } from "../../../testing/salesReturns";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(NOW));
});
afterEach(() => {
  vi.useRealTimers();
});

const MOUSSA = {
  id: "cus-moussa",
  name: "Moussa Abdou",
  phone: "+237690000000",
  kind: "individual",
} as const;
/** La Sanya SY125-8 à 650 000 au comptant, vendue à Moussa. */
const SANYA_TO_MOUSSA: RecordSaleCommand = { ...ONE_SANYA, customer: MOUSSA };

/** Sanya rendue, Haojue HJ125-8 (780 000) remise, nouvelle vente « À crédit ». */
async function creditExchange(command: RecordSaleCommand) {
  const view = await openReturn(command);
  const { user } = view;
  await user.click(
    screen.getByRole("button", { name: "Quantité rendue — Sanya SY125-8 : plus un" }),
  );
  await user.type(screen.getByLabelText("Motif du retour"), "Le client préfère la Haojue");
  await user.click(screen.getByRole("radio", { name: "Échange" }));
  await user.click(await articleButton("Haojue HJ125-8"));
  await user.click(screen.getByRole("radio", { name: "À crédit" }));
  return view;
}

describe("échange à crédit", () => {
  it("client d'origine imposé, acompte, le reste devient une créance", async () => {
    const { user, server, container } = await creditExchange(SANYA_TO_MOUSSA);
    expect(screen.getByText(/Client : celui de la vente d'origine/)).toBeVisible();
    await user.type(screen.getByLabelText("Acompte versé aujourd'hui"), "30000");
    expect(plain(document.body.textContent)).toContain(`Reste à payer${money(100_000)}`);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));

    expect(await screen.findByText(/Échange enregistré — nouvelle vente/)).toBeVisible();
    const body = server.recordReturn.mock.calls[0]?.[1] as SaleReturnCommand;
    expect(body.exchange?.sale).toMatchObject({
      kind: "credit",
      customer: { id: "cus-moussa" },
      payments: [{ mode_id: "pm-cash", amount: 30_000 }],
      credit: { reminder_on: null, terms: null, guarantor: null },
    });
    const sales = [...server.world.sales.values()].map((entry) => entry.result);
    const created = sales.find((sale) => sale.kind === "credit");
    expect(created?.remaining).toBe(100_000);
  });

  it("vente d'origine sans client : échange à crédit refusé avant l'envoi", async () => {
    const { user, server } = await creditExchange(ONE_SANYA);
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));
    expect(
      screen.getByText("La vente d'origine n'a pas de client : l'échange à crédit est impossible"),
    ).toBeVisible();
    expect(server.recordReturn).not.toHaveBeenCalled();
  });

  it("acompte égal à la différence : il faut choisir « Comptant »", async () => {
    const { user, server } = await creditExchange(SANYA_TO_MOUSSA);
    await user.type(screen.getByLabelText("Acompte versé aujourd'hui"), "130000");
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));
    expect(screen.getByText(/L'acompte doit rester inférieur à/)).toBeVisible();
    expect(server.recordReturn).not.toHaveBeenCalled();
  });
});
