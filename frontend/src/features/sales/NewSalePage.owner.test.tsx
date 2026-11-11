import { screen } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  articleButton,
  preloadSales,
  renderSale,
  sentSale,
  validateButton,
} from "../../testing/renderSale";
import { json } from "../../testing/fakeApi";
import { saleProfile } from "../../testing/salesCatalog";
import { API } from "../../testing/salesServer";
import { NO_USUAL_LOCATION } from "./saleLocation";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
});

describe("lieu de vente et en-têtes envoyés", () => {
  it("propriétaire : choisit le point de vente ; le stock et l'envoi suivent ce lieu", async () => {
    const { user, recordSale, fake, container } = renderSale("owner");
    const garoua = await screen.findByRole("radio", { name: "Garoua" });
    expect(garoua).toHaveAttribute("aria-checked", "true");
    expect(screen.queryByRole("radio", { name: "Dépôt Garoua-Boulaï" })).toBeNull();
    await user.click(screen.getByRole("radio", { name: "Ngaoundéré" }));
    await user.click(await articleButton("Haojue HJ125-8"));
    expect(screen.getByText("Stock disponible à Ngaoundéré : 6")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    expect(sentSale(recordSale).location_id).toBe("loc-ngaoundere");
    const post = fake.calls.find((c) => c.method === "POST" && c.url === `${API}/sales`);
    expect(post?.headers.get("X-Captured-At")).toMatch(/T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$/);
  });

  it("vendeur : son lieu habituel, sans choix ; 360 px sans conteneur qui élargit la page", async () => {
    const { user, recordSale, container } = renderSale("seller");
    await user.click(await articleButton("Sanya SY125-8"));
    expect(screen.queryByRole("radiogroup", { name: "Lieu de vente" })).toBeNull();
    expect(screen.getByText("Stock disponible à Garoua : 7")).toBeVisible();
    expect(container.querySelector("table")).toBeNull();
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    expect(sentSale(recordSale).location_id).toBe("loc-garoua");
  });

  it("vendeur sans lieu habituel : message clair, aucune vente possible", async () => {
    const profile = { ...saleProfile("seller"), default_location_id: null };
    renderSale("seller", { extra: { [`GET ${API}/profile`]: json(200, profile) } });
    expect(await screen.findByText(NO_USUAL_LOCATION)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Valider la vente" })).toBeNull();
  });
});
