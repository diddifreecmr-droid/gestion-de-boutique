import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { json } from "../testing/fakeApi";
import { renderApp } from "../testing/renderApp";
import {
  preloadSettings,
  profileWithRoles,
  route,
  settingsRoutes,
  viewPath,
} from "../testing/shopSettingsApi";

const LOGO_PATH = "/api/v1/shops/s/attachments/a/content?expires=1&signature=x";

beforeAll(preloadSettings);
beforeEach(() => {
  window.localStorage.clear();
});

function open(logo: { url: string; expires_at: string } | null) {
  const routes = settingsRoutes("owner");
  routes[route("GET", "/profile")] = json(200, { ...profileWithRoles(), logo });
  return renderApp(viewPath("boutique"), routes);
}

describe("logo dans la coquille de la boutique (specs § 15.1)", () => {
  it("logo servi : à gauche du nom dans la barre du haut, et en filigrane", async () => {
    const { container } = open({ url: LOGO_PATH, expires_at: "2026-11-24T10:01:00Z" });
    const banner = await screen.findByRole("banner");
    const image = banner.querySelector("img");
    expect(image?.getAttribute("src")).toMatch(/\/api\/v1\/shops\/s\/attachments\/a\/content/);
    expect(within(banner).getByText("Motos Garoua")).toBeVisible();
    const mark = container.querySelector("[data-testid='shop-watermark']");
    expect(mark?.querySelector("img")?.getAttribute("src")).toBe(image?.getAttribute("src"));
  });

  it("sans logo : logo générique aux initiales, filigrane avec le nom", async () => {
    const { container } = open(null);
    const banner = await screen.findByRole("banner");
    expect(banner.querySelector("img")).toBeNull();
    expect(banner).toHaveTextContent("MGMotos Garoua");
    const mark = container.querySelector("[data-testid='shop-watermark']");
    expect(mark).toHaveAttribute("aria-hidden", "true");
    expect(mark).toHaveTextContent("Motos Garoua");
  });
});
