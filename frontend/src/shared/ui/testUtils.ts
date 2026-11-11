import { expect, vi } from "vitest";

/**
 * Vérifie qu'un rendu lève l'erreur attendue (fail-fast), sans laisser React et jsdom la
 * recopier en console. Réservé aux tests : jamais importé par l'application.
 */
export function expectRenderError(renderFn: () => unknown, message: string | RegExp): void {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  const silence = (event: ErrorEvent) => {
    event.preventDefault();
  };
  window.addEventListener("error", silence);
  try {
    expect(renderFn).toThrow(message);
  } finally {
    window.removeEventListener("error", silence);
  }
}
