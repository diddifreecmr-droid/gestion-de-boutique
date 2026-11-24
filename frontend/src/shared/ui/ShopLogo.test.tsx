import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { initialsOf, ShopLogo, ShopWatermark, TopBar } from "./index";

describe("initiales du logo générique", () => {
  it("deux premiers mots, capitales, accents gardés ; nom sans lettre refusé", () => {
    expect(initialsOf("Motos Garoua")).toBe("MG");
    expect(initialsOf("Textile")).toBe("T");
    expect(initialsOf("  élégance d'Afrique  Douala")).toBe("ÉD");
    expect(initialsOf("3 Frères - Bafoussam")).toBe("3F");
    expect(() => initialsOf("— !")).toThrow(/sans lettre/);
  });
});

describe("ShopLogo", () => {
  it("image envoyée ; illisible ou lien expiré → initiales (jamais d'image cassée)", () => {
    const { container } = render(<ShopLogo name="Motos Garoua" src="/logo.png" />);
    const image = container.querySelector("img");
    expect(image).toHaveAttribute("src", "/logo.png");
    expect(image).toHaveAttribute("alt", "");
    expect(image).toHaveClass("size-(--logo-sm)", "object-contain");
    fireEvent.error(image as HTMLImageElement);
    expect(container.querySelector("img")).toBeNull();
    expect(container).toHaveTextContent("MG");
  });

  it("sans image : badge `primary` aux initiales, décoratif par défaut, nommé si `alt`", () => {
    const { container } = render(<ShopLogo name="Motos Garoua" src={null} size="md" />);
    const badge = container.firstElementChild;
    expect(badge).toHaveAttribute("aria-hidden", "true");
    expect(badge).toHaveClass("bg-primary", "text-on-primary", "size-(--logo-md)");
    render(<ShopLogo name="Motos Garoua" src={null} alt="Logo générique" />);
    expect(screen.getByRole("img", { name: "Logo générique" })).toHaveTextContent("MG");
  });
});

describe("ShopWatermark", () => {
  it("très pâle, derrière le contenu, ignoré du toucher et des lecteurs d'écran ; nom si générique", async () => {
    const { container } = render(<ShopWatermark name="Motos Garoua" src={null} />);
    const mark = screen.getByTestId("shop-watermark");
    expect(mark).toHaveAttribute("aria-hidden", "true");
    expect(mark).toHaveClass(
      "pointer-events-none",
      "fixed",
      "-z-10",
      "opacity-(--opacity-watermark)",
    );
    expect(mark).toHaveTextContent("MGMotos Garoua");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("avec un logo : l'image seule, sans le nom", () => {
    render(<ShopWatermark name="Motos Garoua" src="/logo.png" />);
    const mark = screen.getByTestId("shop-watermark");
    expect(mark.querySelector("img")).toHaveAttribute("src", "/logo.png");
    expect(mark).not.toHaveTextContent("Motos Garoua");
  });
});

describe("TopBar avec logo", () => {
  it("logo à gauche du nom, le nom reste le titre ; axe", async () => {
    const { container } = render(
      <TopBar
        title="Motos Garoua"
        logo={<ShopLogo name="Motos Garoua" src={null} />}
        alertCount={0}
        onAlertsClick={vi.fn()}
      />,
    );
    const banner = screen.getByRole("banner");
    expect(banner.firstElementChild).toHaveTextContent("MG");
    expect(screen.getByText("Motos Garoua")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });
});
