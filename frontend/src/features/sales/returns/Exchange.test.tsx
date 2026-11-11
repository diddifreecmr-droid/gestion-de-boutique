import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { SaleReturnCommand } from "../../../core/gateways/returnsContract";
import { axeViolations } from "../../../testing/axe";
import { SHOP_A } from "../../../testing/fakeApi";
import { articleButton, money, plain, preloadSales, renderSale } from "../../../testing/renderSale";
import { cancelled, NOW } from "../../../testing/salesFixtures";
import { ONE_SANYA, openReturn, openSaleSheet } from "../../../testing/salesReturns";
import { addSale, API } from "../../../testing/salesServer";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(NOW));
});
afterEach(() => {
  vi.useRealTimers();
});

/** Rend la Sanya en entier, motif saisi, type « Échange ». */
async function startExchange() {
  const view = await openReturn(ONE_SANYA);
  await view.user.click(
    screen.getByRole("button", { name: "Quantité rendue — Sanya SY125-8 : plus un" }),
  );
  await view.user.type(screen.getByLabelText("Motif du retour"), "Le client préfère la Haojue");
  await view.user.click(screen.getByRole("radio", { name: "Échange" }));
  return view;
}

describe("échange (UC-VEN-09)", () => {
  it("nouvelle vente composée comme « Nouvelle vente », le client paie la différence", async () => {
    const { user, server, container } = await startExchange();
    await user.click(await articleButton("Haojue HJ125-8"));
    const balance = plain(screen.getByLabelText("Différence de l'échange").textContent);
    expect(balance).toContain(`Avoir du client${money(650_000)}`);
    expect(balance).toContain(`Nouvelle vente${money(780_000)}`);
    expect(balance).toContain(`À payer par le client${money(130_000)}`);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));

    expect(await screen.findByText("Échange enregistré — nouvelle vente V-000125")).toBeVisible();
    const body = server.recordReturn.mock.calls[0]?.[1] as SaleReturnCommand;
    expect(body.refund).toBeNull();
    expect(body.exchange).toMatchObject({
      mode_id: "pm-cash",
      sale: {
        kind: "cash",
        customer: null,
        lines: [{ article_id: "art-hj125-8", quantity: "1", unit_price: 780_000 }],
        payments: [{ mode_id: "pm-cash", amount: 130_000 }],
      },
    });
    const returns = await screen.findByRole("region", { name: "Retours" });
    expect(plain(returns.textContent)).toContain("Échange du 11/11/2026");
    await user.click(within(returns).getByRole("button", { name: "Voir la nouvelle vente" }));
    expect(await screen.findByRole("heading", { name: "Vente V-000125" })).toBeVisible();
  });

  it("article remis moins cher : la différence est rendue au client", async () => {
    const { user } = await startExchange();
    await user.click(await articleButton("Nanfang NF125-2"));
    const balance = plain(screen.getByLabelText("Différence de l'échange").textContent);
    expect(balance).toContain(`À rendre au client${money(30_000)}`);
  });

  it("échange sans article remis : refusé avant l'envoi", async () => {
    const { user, server } = await startExchange();
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));
    expect(screen.getByText("Ajoutez l'article remis au client")).toBeVisible();
    expect(server.recordReturn).not.toHaveBeenCalled();
  });
});

describe("retours vus selon le rôle et l'état de la vente", () => {
  it("vendeur : retours visibles sans coût ni marge, aucune action de retour", async () => {
    const owner = await openSaleSheet("owner", ONE_SANYA);
    expect(screen.getByRole("button", { name: "Annuler la vente" })).toBeVisible();
    owner.unmount();

    const { server, fake, router, container } = renderSale("seller", {
      path: `/s/${SHOP_A}/mes-ventes`,
    });
    const sale = await addSale(server, ONE_SANYA);
    const line = { line: 1, article_id: "art-sy125-8", article_name: "Sanya SY125-8" };
    server.returns.set(sale.id, [
      {
        id: "ret-1",
        sale_id: sale.id,
        sale_number: sale.number,
        kind: "return",
        lines: [
          {
            ...line,
            quantity: "1",
            stock_quantity: "1",
            stock_unit: "unit",
            condition: "sellable",
            amount: 650_000,
            chassis: [],
          },
        ],
        reason: "Erreur de modèle",
        amount: 650_000,
        refund: { amount: 650_000, mode_id: "pm-cash", refunded_on: "2026-11-11" },
        credit_reduction: 0,
        exchange_sale_id: null,
        returned_at: NOW,
        returned_on: "2026-11-11",
        created_by: server.userId,
      },
    ]);
    await router.navigate(`?id=${sale.id}`);
    const returns = await screen.findByRole("region", { name: "Retours" });
    expect(plain(returns.textContent)).toContain("Motif : Erreur de modèle");
    const read = fake.calls.find((c) => c.url === `${API}/sales/${sale.id}/returns`);
    expect(read).toBeDefined();
    expect(container.textContent).not.toMatch(/coût|marge|CMP/i);
    expect(screen.queryByRole("button", { name: "Retour ou échange" })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("propriétaire : la marge retirée par le retour est affichée", async () => {
    const { user } = await openReturn();
    await user.click(
      screen.getByRole("button", { name: "Quantité rendue — Haojue HJ125-8 : plus un" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Quantité rendue — Haojue HJ125-8 : plus un" }),
    );
    await user.type(screen.getByLabelText("Motif du retour"), "Erreur");
    await user.click(screen.getByRole("button", { name: "Enregistrer le retour" }));
    const returns = await screen.findByRole("region", { name: "Retours" });
    expect(plain(returns.textContent)).toContain(`Marge retirée : ${money(260_000)}`);
  });

  it("vente annulée : aucun retour possible", async () => {
    const { server, router } = renderSale("owner", { path: `/s/${SHOP_A}/ventes` });
    const sale = await addSale(server, ONE_SANYA);
    server.sales.set(sale.id, cancelled(sale, "Erreur"));
    await router.navigate(`?id=${sale.id}`);
    await screen.findByRole("heading", { name: `Vente ${sale.number}` });
    expect(screen.queryByRole("button", { name: "Retour ou échange" })).toBeNull();
    await router.navigate(`?id=${sale.id}&vue=retour`);
    expect(
      await screen.findByText("Cette vente est annulée : aucun retour n'est possible."),
    ).toBeVisible();
  });
});
