/**
 * Prix sous le minimum, réglage « Accord du propriétaire » **désactivé** (défaut, décision
 * client specs § 15.1) : avertissement non bloquant, vente enregistrée, avertissement repris
 * sur la confirmation. Le parcours avec accord est couvert par `NewSalePage.errors.test.tsx`.
 */
import { screen } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  articleButton,
  plain,
  preloadSales,
  priceField,
  renderSale,
  replaceText,
  saleAlert,
  sentSale,
  validateButton,
} from "../../testing/renderSale";
import { BELOW_MINIMUM } from "./useSaleSubmit";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
});

const ASK = "Demander l'accord du propriétaire";

describe("prix sous le minimum, accord non exigé (défaut)", () => {
  it("vendeur : avertissement, « Valider » actif, la vente part sans demande", async () => {
    const { user, recordSale, requestPriceApproval, container } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "700000");
    const warning = screen.getByText(/Sous le prix minimum \(/);
    expect(plain(warning.textContent)).toBe(
      "Sous le prix minimum (720 000 FCFA) : la vente sera notée au journal",
    );
    expect(screen.queryByRole("button", { name: ASK })).toBeNull();
    expect(validateButton()).not.toHaveAttribute("aria-disabled");
    expect(await axeViolations(container)).toEqual([]);

    await user.click(validateButton());
    expect(await screen.findByRole("heading", { name: /V-000124/ })).toBeVisible();
    const texts = screen.getAllByRole("status").map((node) => plain(node.textContent));
    expect(texts).toContain(
      "Prix inférieur au minimum de 720 000 FCFA (ligne 1). Vente enregistrée.",
    );
    expect(sentSale(recordSale).price_request_id).toBeNull();
    expect(requestPriceApproval).not.toHaveBeenCalled();
  });

  it("réglage activé entre-temps : le serveur refuse, l'écran passe à « Demander l'accord »", async () => {
    const { user, server } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "700000");
    server.world.settings.minPriceRequiresApproval = true;
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(BELOW_MINIMUM);
    expect(screen.getByRole("button", { name: ASK })).toBeVisible();
    const line = screen.getByText(/Sous le prix minimum \(720 000 FCFA\)/);
    expect(line).toHaveTextContent("validation du propriétaire nécessaire");
  });
});
