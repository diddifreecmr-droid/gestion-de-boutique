import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { beforeEach, describe, expect, it, vi } from "vitest";
import UiShowcase from "./UiShowcase";

/**
 * jsdom ne calcule ni la mise en page ni les styles : `color-contrast` ne peut pas y être
 * jugé (contrastes calculés dans design-system.md § 2.1, revérifiés par axe dans le
 * navigateur des tests E2E, T24). Toutes les autres règles d'axe s'appliquent.
 */
const AXE_OPTIONS: axe.RunOptions = { rules: { "color-contrast": { enabled: false } } };

async function violations(root: HTMLElement): Promise<string[]> {
  const results = await axe.run(root, AXE_OPTIONS);
  return results.violations.map(
    (violation) =>
      `${violation.id} (${violation.impact ?? "?"}) : ${violation.nodes
        .map((node) => node.target.join(" "))
        .join(" | ")}`,
  );
}

/** Bouton d'ouverture, cherché dans la section ConfirmDialog (d'autres boutons ont ce nom). */
function dialogOpener(name: string): HTMLElement {
  return within(screen.getByRole("region", { name: "ConfirmDialog" })).getByRole("button", {
    name,
  });
}

describe("vitrine /_ui — accessibilité (axe-core)", () => {
  beforeEach(() => {
    // axe sonde un <canvas> que jsdom n'implémente pas : on répond « indisponible » sans bruit.
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  });

  it("le banc détecte bien une violation (témoin)", async () => {
    const { container } = render(
      <main>
        <button type="button">
          <svg aria-hidden="true" />
        </button>
      </main>,
    );
    expect((await violations(container)).join()).toContain("button-name");
  });

  it("chaque composant et ses états : aucune violation", async () => {
    const { container } = render(<UiShowcase />);
    expect(await violations(container)).toEqual([]);
  });

  it("avec les toasts affichés : aucune violation", async () => {
    const user = userEvent.setup();
    const { container } = render(<UiShowcase />);
    await user.click(screen.getByRole("button", { name: "Afficher un succès (4 s)" }));
    await user.click(screen.getByRole("button", { name: "Afficher une erreur" }));
    expect(within(screen.getByRole("alert")).getByText(/Échec de l'envoi/)).toBeVisible();
    expect(await violations(container)).toEqual([]);
  });

  it.each([
    ["Se déconnecter", "Se déconnecter ?"],
    ["Annuler la vente", "Annuler la vente V-000124 ?"],
  ])("avec la confirmation « %s » ouverte : aucune violation", async (opener, title) => {
    const user = userEvent.setup();
    const { container } = render(<UiShowcase />);
    await user.click(dialogOpener(opener));
    expect(screen.getByRole("dialog", { name: title })).toBeVisible();
    expect(await violations(container)).toEqual([]);
  });

  it("avec « Plus de détails » ouvert et une saisie en erreur : aucune violation", async () => {
    const user = userEvent.setup();
    const { container } = render(<UiShowcase />);
    const [disclosure] = screen.getAllByRole("button", { name: "Plus de détails" });
    if (disclosure === undefined) throw new Error("Disclosure absent de la vitrine");
    await user.click(disclosure);
    await user.click(dialogOpener("Annuler la vente"));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Annuler la vente" }));
    expect(screen.getByText("Le motif est obligatoire")).toBeVisible();
    expect(await violations(container)).toEqual([]);
  });
});
