import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Check } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { buttonClasses } from "./buttonClasses";
import { Button, LOADING_LABEL, type ButtonVariant } from "./index";

describe("Button", () => {
  it("rend un bouton accessible par son libellé, de type button par défaut", () => {
    render(<Button>Valider la vente</Button>);
    const button = screen.getByRole("button", { name: "Valider la vente" });
    expect(button).toHaveAttribute("type", "button");
    expect(button).not.toHaveAttribute("aria-disabled");
  });

  it("transmet le clic", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Valider</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Valider" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it.each<[ButtonVariant, string]>([
    ["primary", "bg-primary"],
    ["secondary", "border-border-strong"],
    ["ghost", "bg-transparent"],
    ["danger", "bg-danger"],
  ])("applique la variante %s", (variant, expected) => {
    render(<Button variant={variant}>Action</Button>);
    expect(screen.getByRole("button")).toHaveClass(expected);
  });

  it("utilise les tokens de hauteur md (48 px) et lg (56 px)", () => {
    render(
      <>
        <Button>Moyen</Button>
        <Button size="lg">Grand</Button>
      </>,
    );
    expect(screen.getByRole("button", { name: "Moyen" })).toHaveClass("min-h-(--control-md)");
    expect(screen.getByRole("button", { name: "Grand" })).toHaveClass("min-h-(--control-lg)");
  });

  it("a un anneau de focus visible", () => {
    render(<Button>Focus</Button>);
    expect(screen.getByRole("button")).toHaveClass(
      "focus-visible:ring-2",
      "focus-visible:ring-primary",
    );
  });

  it("affiche l'icône à côté du mot, masquée des lecteurs d'écran", () => {
    const { container } = render(<Button icon={Check}>Valider</Button>);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("button", { name: "Valider" })).toBeInTheDocument();
  });

  it("indisponible : affiche la raison, la relie et bloque le clic", async () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabledReason="Choisissez d'abord un article">
        Valider
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Valider" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveAccessibleDescription("Choisissez d'abord un article");
    expect(button).toHaveClass("opacity-50");
    expect(button.className).not.toMatch(/hover:/);
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("conserve une description fournie en plus de la raison", () => {
    render(
      <>
        <p id="aide">Aide</p>
        <Button aria-describedby="aide" disabledReason="Hors connexion">
          Envoyer
        </Button>
      </>,
    );
    expect(screen.getByRole("button")).toHaveAccessibleDescription("Aide Hors connexion");
  });

  it("refuse une raison vide (fail-fast)", () => {
    // L'erreur est attendue : on évite seulement que React et jsdom la recopient en console.
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const silence = (event: ErrorEvent) => {
      event.preventDefault();
    };
    window.addEventListener("error", silence);
    expect(() => render(<Button disabledReason="  ">Valider</Button>)).toThrow(
      "disabledReason ne peut pas être vide",
    );
    window.removeEventListener("error", silence);
  });

  it("chargement : libellé « Envoi… » et double appui bloqué", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Valider
      </Button>,
    );
    const button = screen.getByRole("button", { name: LOADING_LABEL });
    expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.dblClick(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("pleine largeur, y compris avec une raison", () => {
    render(
      <Button fullWidth disabledReason="Hors connexion">
        Valider
      </Button>,
    );
    expect(screen.getByRole("button")).toHaveClass("w-full");
    expect(buttonClasses("primary", "md", false, false)).not.toContain("w-full");
  });
});
