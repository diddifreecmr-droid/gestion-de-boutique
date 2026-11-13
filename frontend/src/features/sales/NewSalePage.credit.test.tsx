import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  articleButton,
  money,
  plain,
  priceField,
  renderSale,
  replaceText,
  validateButton,
  preloadSales,
  saleAlert,
} from "../../testing/renderSale";
import { FIX_FIELDS } from "./useSaleSubmit";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
});

const radio = (name: string, group: string) =>
  within(screen.getByRole("radiogroup", { name: group })).getByRole("radio", { name });

async function startCredit(user: ReturnType<typeof renderSale>["user"]) {
  await user.click(await articleButton("Haojue HJ125-8"));
  await user.click(radio("À crédit", "Paiement"));
}

describe("Nouvelle vente à crédit (UC-VEN-02)", () => {
  it("client obligatoire (nom + téléphone) : refus sans client", async () => {
    const { user, recordSale, container } = renderSale();
    await startCredit(user);
    await user.click(validateButton());
    expect(screen.getByText(FIX_FIELDS)).toBeVisible();
    expect(
      screen.getByText("Client obligatoire pour une vente à crédit (nom et téléphone)"),
    ).toBeVisible();
    expect(recordSale).not.toHaveBeenCalled();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("création rapide du client : téléphone contrôlé, acompte, reste à payer", async () => {
    const { user, recordSale, container } = renderSale();
    await startCredit(user);
    await user.click(screen.getByRole("button", { name: "Nouveau client" }));
    await user.type(screen.getByLabelText("Nom du client"), "Ibrahim Oumarou");
    await user.type(screen.getByLabelText("Téléphone du client"), "69011");
    await user.click(validateButton());
    expect(screen.getByText("Le téléphone doit avoir 9 chiffres")).toBeVisible();
    await user.type(screen.getByLabelText("Téléphone du client"), "2233");

    await user.type(priceField("Acompte versé aujourd'hui"), "300000");
    expect(radio("Espèces", "Mode de l'acompte")).toHaveAttribute("aria-checked", "true");
    const summary = screen.getByText("Reste à payer").closest("dl");
    if (summary === null) throw new Error("Récapitulatif absent");
    expect(plain(summary.textContent)).toContain(money(780_000));
    expect(plain(summary.textContent)).toContain(money(300_000));
    expect(within(summary).getByText(money(480_000))).toHaveClass("text-credit-text");
    expect(await axeViolations(container)).toEqual([]);

    await user.click(validateButton());
    expect(await screen.findByRole("heading", { name: /V-000124/ })).toBeVisible();
    expect(screen.getByText("Vente à crédit")).toBeVisible();
    expect(screen.getByText(money(480_000))).toBeVisible();
    const [, command] = recordSale.mock.calls[0] ?? [];
    expect(command).toMatchObject({
      kind: "credit",
      customer: { id: null, name: "Ibrahim Oumarou", phone: "+237690112233", kind: "individual" },
      payments: [{ mode_id: "pm-cash", amount: 300_000, reference: null }],
      credit: { reminder_on: null, terms: null, guarantor: null },
    });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("acompte à 0, client existant, rappel et conditions", async () => {
    const { user, recordSale } = renderSale();
    await startCredit(user);
    await user.type(screen.getByLabelText("Chercher un client"), "mou");
    await user.click(await screen.findByRole("button", { name: /Moussa Abdou/ }));
    expect(screen.getByText("+237690000000")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Plus de détails : rappel, conditions" }));
    await user.type(screen.getByLabelText("Date de rappel"), "2026-12-01");
    await user.type(screen.getByLabelText("Conditions convenues"), "100 000 par mois");
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    const [, command] = recordSale.mock.calls[0] ?? [];
    expect(command).toMatchObject({
      customer: { id: "cus-moussa", name: "Moussa Abdou" },
      payments: [],
      credit: { reminder_on: "2026-12-01", terms: "100 000 par mois", guarantor: null },
    });
  });

  it("acompte supérieur au total : refusé", async () => {
    const { user, recordSale } = renderSale();
    await startCredit(user);
    await user.type(priceField("Acompte versé aujourd'hui"), "900000");
    expect(screen.getByText(/L'acompte dépasse le montant de la vente/)).toBeVisible();
    await user.click(validateButton());
    expect(recordSale).not.toHaveBeenCalled();
  });

  it("plafond de crédit dépassé : le vendeur est refusé", async () => {
    const { user } = renderSale();
    await startCredit(user);
    await user.type(screen.getByLabelText("Chercher un client"), "garba");
    await user.click(await screen.findByRole("button", { name: /Garba Transport/ }));
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(/Plafond de crédit dépassé/);
  });

  it("plafond de crédit dépassé : le propriétaire passe, avec un avertissement", async () => {
    const { user } = renderSale("owner");
    await startCredit(user);
    await user.type(screen.getByLabelText("Chercher un client"), "677112");
    await user.click(await screen.findByRole("button", { name: /Garba Transport/ }));
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    expect(
      screen.getByText(/Plafond de crédit dépassé : ce client doit maintenant 1 080 000/),
    ).toBeVisible();
  });
});

describe("Paiement réparti sur plusieurs modes (RG-T20)", () => {
  it("total payé ≤ total : dépassement refusé, manque signalé, puis envoi", async () => {
    const { user, recordSale, container } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await user.click(screen.getByRole("button", { name: "Autre mode" }));
    await user.click(screen.getByRole("button", { name: "Répartir sur plusieurs modes" }));
    const cash = priceField("Espèces");
    expect(plain(cash.value)).toBe("780 000");
    await replaceText(user, cash, "500000");
    await user.type(priceField("Orange Money"), "400000");
    expect(screen.getByText(/Le total payé .* dépasse le montant de la vente/)).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(validateButton());
    expect(screen.getByText(FIX_FIELDS)).toBeVisible();
    expect(recordSale).not.toHaveBeenCalled();

    await replaceText(user, priceField("Orange Money"), "260000");
    expect(screen.getByText(/Il manque 20 000 FCFA/)).toBeVisible();
    await replaceText(user, priceField("Orange Money"), "280000");
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    expect(recordSale).toHaveBeenCalledTimes(1);
    const [, command] = recordSale.mock.calls[0] ?? [];
    expect(command?.payments).toEqual([
      { mode_id: "pm-cash", amount: 500_000, reference: null },
      { mode_id: "pm-orange", amount: 280_000, reference: null },
    ]);
  });

  it("revenir à un seul mode", async () => {
    const { user } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await user.click(screen.getByRole("button", { name: "Autre mode" }));
    await user.click(screen.getByRole("button", { name: "Répartir sur plusieurs modes" }));
    expect(priceField("Orange Money")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Payer avec un seul mode" }));
    expect(screen.queryByLabelText("Orange Money")).toBeNull();
  });
});
