import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { json } from "../../testing/fakeApi";
import {
  CUSTOMER,
  LIST,
  listing,
  preloadReceivables,
  receivable,
  receivableRoutes,
  RECEIVABLES_PATH,
  SEARCH,
} from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";

beforeAll(preloadReceivables);
beforeEach(() => {
  window.localStorage.clear();
});

const amountField = () => screen.getByLabelText("Montant du versement");
const afterText = () => plain(screen.getByText(/Reste à payer après ce versement/).textContent);

describe("Versement : choix de la créance du client (REC-03)", () => {
  it("plusieurs créances : la plus ancienne par défaut, l'autre au choix ; sans créance, message", async () => {
    const newer = receivable({
      id: "sale-200",
      sale_number: "V-000200",
      opened_on: "2026-11-05",
      remaining: 90000,
    });
    const lost = receivable({
      id: "sale-050",
      sale_number: "V-000050",
      opened_on: "2026-01-05",
      status: "written_off",
    });
    const { user } = renderApp(`${RECEIVABLES_PATH}?vue=versement`, {
      ...receivableRoutes("owner"),
      [SEARCH]: json(200, { items: [CUSTOMER] }),
      [LIST]: json(200, listing([newer, lost, receivable()])),
    });
    await user.click(await screen.findByLabelText("Chercher le client"));
    await user.paste("Moussa");
    await user.click(await screen.findByRole("button", { name: /Moussa Hamadou/ }));
    const chips = await screen.findByRole("radiogroup", { name: "Créance à payer" });
    const options = within(chips).getAllByRole("radio");
    expect(options.map((o) => plain(o.textContent))).toEqual([
      `La plus ancienne : Vente V-000124 — reste ${money(600000)}`,
      `Vente V-000200 — reste ${money(90000)}`,
      `Vente V-000050 — reste ${money(600000)}`,
    ]);
    expect(options[0]).toHaveAttribute("aria-checked", "true");
    await user.click(within(chips).getByRole("radio", { name: /V-000200/ }));
    await user.type(amountField(), "10000");
    expect(afterText()).toBe(`Reste à payer après ce versement : ${money(80000)}`);
    await user.click(screen.getByRole("button", { name: "Changer de client" }));
    expect(screen.getByLabelText("Chercher le client")).toBeVisible();
  });

  it("client sans créance à payer : message et changement de client", async () => {
    const { user } = renderApp(`${RECEIVABLES_PATH}?vue=versement`, {
      ...receivableRoutes("seller"),
      [SEARCH]: json(200, { items: [CUSTOMER] }),
      [LIST]: json(200, listing([receivable({ remaining: 0, status: "settled" })])),
    });
    await user.click(await screen.findByLabelText("Chercher le client"));
    await user.paste("Moussa");
    await user.click(await screen.findByRole("button", { name: /Moussa Hamadou/ }));
    expect(await screen.findByText("Moussa Hamadou n'a aucune créance à payer.")).toBeVisible();
  });
});
