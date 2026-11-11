import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { REASON_REQUIRED } from "../../shared/ui";
import { axeViolations } from "../../testing/axe";
import { SHOP_A } from "../../testing/fakeApi";
import { money, plain, preloadSales, renderSale } from "../../testing/renderSale";
import { NOW, report, saleCommand } from "../../testing/salesFixtures";
import { addSale, API, type SaleRole } from "../../testing/salesServer";
import { DESCRIPTION_REQUIRED } from "./ErrorReports";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(NOW));
});
afterEach(() => {
  vi.useRealTimers();
});

const TWO_LINES = saleCommand({
  lines: [
    {
      article_id: "art-hj125-8",
      sale_mode: "unit",
      quantity: "1",
      unit_price: 780_000,
      details: [{ color: "Rouge", chassis_number: "LBX0001", engine_number: "E-77", size: null }],
    },
    {
      article_id: "art-sy125-8",
      sale_mode: "unit",
      quantity: "1",
      unit_price: 650_000,
      details: [],
    },
  ],
  payments: [{ mode_id: "pm-cash", amount: 1_430_000, reference: "R-1" }],
});

async function openSale(role: SaleRole) {
  const view = renderSale(role, {
    path: `/s/${SHOP_A}/${role === "owner" ? "ventes" : "mes-ventes"}`,
  });
  const sale = await addSale(view.server, TWO_LINES);
  await view.router.navigate(`?id=${sale.id}`);
  await screen.findByRole("heading", { name: `Vente ${sale.number}` });
  return { ...view, sale };
}

describe("fiche d'une vente", () => {
  it("propriétaire : lignes, détails, paiements, coûts figés et marges (« non calculable »)", async () => {
    const { container } = await openSale("owner");
    const lines = screen.getByRole("region", { name: "Articles" });
    expect(plain(lines.textContent)).toContain(
      "Couleur : Rouge · Châssis : LBX0001 · Moteur : E-77",
    );
    expect(plain(lines.textContent)).toContain(`Dernier coût figé${money(650_000)}`);
    expect(plain(lines.textContent)).toContain(`Marge${money(130_000)}`);
    expect(within(lines).getAllByText("non calculable")).toHaveLength(4);
    expect(plain(screen.getByRole("region", { name: "Paiements" }).textContent)).toContain(
      `Espèces (R-1)${money(1_430_000)}`,
    );
    expect(screen.getByText("vous")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Signaler une erreur" })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("propriétaire : annuler avec un motif obligatoire, la vente reste barrée « Annulée »", async () => {
    const { user, fake, sale } = await openSale("owner");
    await user.click(screen.getByRole("button", { name: "Annuler la vente" }));
    const dialog = screen.getByRole("dialog", { name: `Annuler la vente ${sale.number} ?` });
    await user.click(within(dialog).getByRole("button", { name: "Annuler la vente" }));
    expect(within(dialog).getByText(REASON_REQUIRED)).toBeVisible();
    await user.type(within(dialog).getByLabelText("Motif"), "Client parti");
    await user.click(within(dialog).getByRole("button", { name: "Annuler la vente" }));
    expect(
      await screen.findByText(/Annulée le 11\/11\/2026 à .* par vous — motif : Client parti/),
    ).toBeVisible();
    expect(screen.getByText("Annulée", { selector: "span" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Annuler la vente" })).toBeNull();
    const cancel = fake.calls.find((c) => c.url === `${API}/sales/${sale.id}/cancel`);
    expect(cancel?.body).toEqual({ reason: "Client parti", refund_payments: false });
  });

  it("vendeur : aucun coût ni marge, « Signaler une erreur » puis la réponse du propriétaire", async () => {
    const { user, fake, sale, container, server } = await openSale("seller");
    expect(container.textContent).not.toMatch(/coût|marge|CMP|calculable/i);
    expect(screen.queryByRole("button", { name: "Annuler la vente" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Signaler une erreur" }));
    await user.click(screen.getByRole("button", { name: "Envoyer au propriétaire" }));
    expect(screen.getByText(DESCRIPTION_REQUIRED)).toBeVisible();
    await user.type(
      screen.getByLabelText("Quel est le problème ?"),
      "Mauvais prix, c'était 750 000",
    );
    await user.click(screen.getByRole("button", { name: "Envoyer au propriétaire" }));
    expect(await screen.findByText("« Mauvais prix, c'était 750 000 »")).toBeVisible();
    expect(screen.getByText("En attente de réponse")).toBeVisible();
    const sent = fake.calls.find((c) => c.url === `${API}/sales/${sale.id}/error-reports`);
    expect(sent?.body).toMatchObject({ description: "Mauvais prix, c'était 750 000" });
    expect(await axeViolations(container)).toEqual([]);

    const answered = { ...report(sale, "r2", "Couleur"), owner_reply: "Corrigé, merci" };
    server.sales.set(sale.id, { ...sale, error_reports: [answered] });
    await user.click(screen.getByRole("button", { name: "Retour aux ventes" }));
    await user.click(await screen.findByRole("link", { name: new RegExp(sale.number) }));
    expect(await screen.findByText("Réponse du propriétaire : Corrigé, merci")).toBeVisible();
  });
});
