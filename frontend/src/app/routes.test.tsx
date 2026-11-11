import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { appRoutes, UI_SHOWCASE_PATH } from "./routes";

function renderAt(path: string) {
  const router = createMemoryRouter(appRoutes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
}

describe("routes", () => {
  it("affiche l'accueil", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { level: 1, name: "Gestion de boutique" })).toBeVisible();
  });

  it("affiche une page introuvable pour une adresse inconnue", () => {
    renderAt("/nulle-part");
    expect(screen.getByRole("heading", { name: "Page introuvable" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Retour à l'accueil" })).toHaveAttribute("href", "/");
  });

  it("sert la vitrine /_ui en développement, avec les boutons et la palette", async () => {
    expect(import.meta.env.DEV).toBe(true);
    renderAt(UI_SHOWCASE_PATH);
    expect(await screen.findByRole("heading", { name: "Vitrine des composants" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Button" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Palette" })).toBeVisible();
    expect(screen.getByText("--color-primary")).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Valider la vente" }).length).toBeGreaterThan(0);
  });
});
