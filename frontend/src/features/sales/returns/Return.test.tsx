import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { SaleReturnCommand } from "../../../core/gateways/returnsContract";
import { axeViolations } from "../../../testing/axe";
import { money, plain, preloadSales, replaceText, saleAlert } from "../../../testing/renderSale";
import { NOW } from "../../../testing/salesFixtures";
import { CREDIT_MOTO, openReturn } from "../../../testing/salesReturns";
import { HAS_RETURN } from "./returnErrorMessage";
import { FIX_RETURN } from "./ReturnForm";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(NOW));
});
afterEach(() => {
  vi.useRealTimers();
});

const PLUS = "Quantité rendue — Haojue HJ125-8 : plus un";
const SAVE = "Enregistrer le retour";

function sent(recordReturn: { mock: { calls: unknown[][] } }): SaleReturnCommand {
  const call = recordReturn.mock.calls[0];
  if (call === undefined) throw new Error("Aucun retour envoyé");
  return call[1] as SaleReturnCommand;
}

function amountField(label: string): HTMLInputElement {
  const field = screen.getByLabelText(label);
  if (!(field instanceof HTMLInputElement)) throw new Error(`« ${label} » n'est pas un champ`);
  return field;
}

describe("retour simple (UC-VEN-09)", () => {
  it("retour partiel : châssis à choisir, remboursement, la vente ne s'annule plus", async () => {
    const { user, server, container } = await openReturn();
    expect(screen.getByText("Encore rendable : 2")).toBeVisible();
    await user.click(screen.getByRole("button", { name: PLUS }));
    const chassis = screen.getByRole("group", { name: "Châssis rendus — Haojue HJ125-8" });
    await user.click(within(chassis).getByRole("button", { name: "LBX0002" }));
    expect(within(chassis).getByRole("button", { name: "LBX0002" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await user.type(screen.getByLabelText("Motif du retour"), "Moteur défectueux");
    expect(plain(screen.getByRole("region", { name: "Remboursement" }).textContent)).toContain(
      `Remboursable au plus${money(780_000)}`,
    );
    await replaceText(user, amountField("Montant remboursé"), "780000");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: SAVE }));

    expect(await screen.findByText(/Retour enregistré — vente V-000124/)).toBeVisible();
    expect(sent(server.recordReturn)).toMatchObject({
      lines: [{ line: 1, quantity: "1", condition: "sellable", chassis: ["LBX0002"] }],
      reason: "Moteur défectueux",
      refund: { amount: 780_000, mode_id: "pm-cash", refunded_on: "2026-11-11" },
      exchange: null,
    });
    const returns = await screen.findByRole("region", { name: "Retours" });
    expect(plain(returns.textContent)).toContain("1 × Haojue HJ125-8 — châssis LBX0002");
    expect(plain(returns.textContent)).toContain(`Remboursé : ${money(780_000)} (Espèces)`);
    expect(screen.queryByRole("button", { name: "Annuler la vente" })).toBeNull();
    expect(screen.getByText(HAS_RETURN)).toBeVisible();
    expect(screen.getByRole("button", { name: "Retour ou échange" })).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("contrôles : ligne, motif, châssis et remboursement plafonné, sans envoi", async () => {
    const { user, server } = await openReturn();
    await user.click(screen.getByRole("button", { name: SAVE }));
    expect(await saleAlert()).toHaveTextContent(FIX_RETURN);
    expect(screen.getByText("Choisissez au moins un article rendu")).toBeVisible();
    expect(screen.getByText("Le motif est obligatoire")).toBeVisible();
    await user.click(screen.getByRole("button", { name: PLUS }));
    expect(screen.getByText("Choisissez 1 châssis rendu(s)")).toBeVisible();
    await replaceText(user, amountField("Montant remboursé"), "900000");
    expect(
      screen.getByText(`Le remboursement ne peut pas dépasser ${money(780_000)}`),
    ).toBeVisible();
    expect(server.recordReturn).not.toHaveBeenCalled();
  });

  it("tout rendre, en stock abîmé : châssis implicites, rien remboursé", async () => {
    const { user, server } = await openReturn();
    await user.click(screen.getByRole("button", { name: PLUS }));
    await user.click(screen.getByRole("button", { name: PLUS }));
    expect(screen.queryByRole("group", { name: /Châssis rendus/ })).toBeNull();
    await user.click(screen.getByRole("radio", { name: "Abîmé" }));
    await user.type(screen.getByLabelText("Motif du retour"), "Choc au transport");
    await user.click(screen.getByRole("button", { name: SAVE }));
    const returns = await screen.findByRole("region", { name: "Retours" });
    expect(sent(server.recordReturn)).toMatchObject({
      lines: [{ line: 1, quantity: "2", condition: "damaged", chassis: [] }],
      refund: null,
    });
    expect(within(returns).getByText("Abîmé")).toBeVisible();
    expect(screen.getByText("Tout a déjà été rendu sur cette vente.")).toBeVisible();
  });

  it("quantité déjà rendue entre-temps : RETURN_QUANTITY_EXCEEDED dit le reste", async () => {
    const { user, server, sale } = await openReturn();
    await user.click(screen.getByRole("button", { name: PLUS }));
    await user.click(screen.getByRole("button", { name: PLUS }));
    await user.type(screen.getByLabelText("Motif du retour"), "Erreur");
    server.returns.set(sale.id, [
      {
        id: "ret-autre",
        sale_id: sale.id,
        sale_number: sale.number,
        kind: "return",
        lines: [
          {
            line: 1,
            article_id: "art-hj125-8",
            article_name: "Haojue HJ125-8",
            quantity: "1",
            stock_quantity: "1",
            stock_unit: "unit",
            condition: "sellable",
            amount: 780_000,
            chassis: ["LBX0001"],
          },
        ],
        reason: "Autre téléphone",
        amount: 780_000,
        refund: null,
        credit_reduction: 0,
        exchange_sale_id: null,
        returned_at: NOW,
        returned_on: "2026-11-11",
        created_by: server.userId,
        margin: null,
        margin_wac: null,
      },
    ]);
    await user.click(screen.getByRole("button", { name: SAVE }));
    expect(await saleAlert()).toHaveTextContent("Ligne 1 : il ne reste que 1 à rendre.");
  });

  it("vente à crédit : la valeur rendue baisse d'abord la créance", async () => {
    const { user, server } = await openReturn(CREDIT_MOTO);
    await user.click(screen.getByRole("button", { name: PLUS }));
    const refund = plain(screen.getByRole("region", { name: "Remboursement" }).textContent);
    expect(refund).toContain(`Valeur rendue${money(780_000)}`);
    expect(refund).toContain(`Baisse de la créance${money(580_000)}`);
    expect(refund).toContain(`Remboursable au plus${money(200_000)}`);
    await user.type(screen.getByLabelText("Motif du retour"), "Client a changé d'avis");
    await user.click(screen.getByRole("button", { name: SAVE }));
    const returns = await screen.findByRole("region", { name: "Retours" });
    expect(sent(server.recordReturn).refund).toBeNull();
    expect(plain(returns.textContent)).toContain(`Baisse de la créance : ${money(580_000)}`);
  });
});
