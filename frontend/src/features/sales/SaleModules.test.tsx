/**
 * Ventes sans le module Créances (décision client du 12/11/2026) : vente comptant possible,
 * aucun « À crédit » (vente, échange, filtre de la liste).
 */
import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { SHOP_A } from "../../testing/fakeApi";
import { MINIMAL, saleProfileWith } from "../../testing/modules";
import { articleButton, preloadSales, renderSale, validateButton } from "../../testing/renderSale";
import { ONE_SANYA, openReturn } from "../../testing/salesReturns";
import { addSale } from "../../testing/salesServer";
import { saleCommand } from "../../testing/salesFixtures";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
});

const radioLabels = (group: string) =>
  within(screen.getByRole("radiogroup", { name: group }))
    .getAllByRole("radio")
    .map((radio) => radio.textContent);

describe("boutique minimale : vente au comptant seulement", () => {
  it("vendeur : modes de paiement sans « À crédit », la vente comptant s'enregistre ; axe", async () => {
    const { user, recordSale, container } = renderSale("seller", {
      extra: saleProfileWith("seller", MINIMAL),
    });
    await user.click(await articleButton("Haojue HJ125-8"));
    expect(radioLabels("Paiement")).not.toContain("À crédit");
    expect(screen.queryByRole("radio", { name: "À crédit" })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(validateButton());
    expect(
      await screen.findByRole("heading", { name: /^Vente enregistrée — reçu n°/ }),
    ).toBeVisible();
    const [, command] = recordSale.mock.calls[0] ?? [];
    expect(command).toMatchObject({ kind: "cash", credit: null });
  });

  it("avec Créances, « À crédit » est proposé (témoin)", async () => {
    const { user } = renderSale("seller");
    await user.click(await articleButton("Haojue HJ125-8"));
    expect(radioLabels("Paiement")).toContain("À crédit");
  });

  it("liste des ventes du propriétaire : pas de filtre « Comptant ou crédit »", async () => {
    const view = renderSale("owner", {
      path: `/s/${SHOP_A}/ventes`,
      extra: saleProfileWith("owner", MINIMAL),
    });
    await addSale(view.server, saleCommand());
    await screen.findByRole("list", { name: "Liste des ventes" });
    await view.user.click(screen.getByRole("button", { name: "Filtres" }));
    expect(screen.getByRole("radiogroup", { name: "Mode de paiement" })).toBeVisible();
    expect(screen.queryByRole("radiogroup", { name: "Comptant ou crédit" })).toBeNull();
  });

  it("échange : la nouvelle vente est au comptant, sans choix « À crédit »", async () => {
    const { user } = await openReturn(ONE_SANYA, saleProfileWith("owner", MINIMAL));
    await user.click(
      screen.getByRole("button", { name: "Quantité rendue — Sanya SY125-8 : plus un" }),
    );
    await user.type(screen.getByLabelText("Motif du retour"), "Le client préfère la Haojue");
    await user.click(screen.getByRole("radio", { name: "Échange" }));
    await user.click(await articleButton("Haojue HJ125-8"));
    expect(screen.getByRole("radiogroup", { name: "Mode de paiement de l'échange" })).toBeVisible();
    expect(screen.queryByRole("radiogroup", { name: "Paiement de la nouvelle vente" })).toBeNull();
    expect(screen.queryByRole("radio", { name: "À crédit" })).toBeNull();
  });
});
