/**
 * axe-core dans jsdom (tests seulement). `color-contrast` ne peut pas y être jugé (pas de
 * calcul de style) : contrastes vérifiés dans design-system.md § 2.1 et par l'E2E (T24).
 */
import axe from "axe-core";
import { vi } from "vitest";

const AXE_OPTIONS: axe.RunOptions = { rules: { "color-contrast": { enabled: false } } };

export async function axeViolations(root: HTMLElement): Promise<string[]> {
  // axe sonde un <canvas> que jsdom n'implémente pas : on répond « indisponible » sans bruit.
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  const results = await axe.run(root, AXE_OPTIONS);
  return results.violations.map(
    (violation) =>
      `${violation.id} (${violation.impact ?? "?"}) : ${violation.nodes
        .map((node) => node.target.join(" "))
        .join(" | ")}`,
  );
}
