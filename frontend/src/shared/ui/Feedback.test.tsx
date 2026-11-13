import { render, screen } from "@testing-library/react";
import { Wrench } from "lucide-react";
import { describe, expect, it } from "vitest";
import { Badge, Banner, EmptyState, Skeleton, type BadgeStatus } from "./index";
import { expectRenderError } from "./testUtils";

describe("Badge", () => {
  it.each<[BadgeStatus, string]>([
    ["credit", "bg-credit-soft"],
    ["success", "bg-success-soft"],
    ["warning", "bg-warning-soft"],
    ["danger", "bg-danger-soft"],
    ["offline", "border-border-strong"],
    ["upcoming", "border-dashed"],
  ])("statut %s : mot + icône, 28 px, --radius-sm", (status, classe) => {
    render(<Badge status={status}>Statut</Badge>);
    const badge = screen.getByText("Statut").parentElement;
    expect(badge).toHaveClass(classe, "min-h-7", "rounded-sm", "text-label");
    expect(badge?.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("refuse une pastille sans mot (P7)", () => {
    expectRenderError(() => render(<Badge status="credit"> </Badge>), "children");
  });
});

describe("Banner", () => {
  it("« Connexion nécessaire » : warning, icône WifiOff, annoncé poliment", () => {
    render(<Banner title="Connexion nécessaire">Réessayez plus tard.</Banner>);
    const banner = screen.getByRole("status");
    expect(banner).toHaveClass("bg-warning-soft", "text-warning-text", "w-full");
    expect(banner).toHaveTextContent("Connexion nécessaireRéessayez plus tard.");
    expect(banner.querySelector("svg")).toHaveClass("lucide-wifi-off");
  });

  it("accepte une autre icône et une action", () => {
    render(<Banner title="Maintenance" icon={Wrench} action={<a href="#a">Détails</a>} />);
    expect(screen.getByRole("link", { name: "Détails" })).toBeVisible();
    expectRenderError(() => render(<Banner title="" />), "title");
  });
});

describe("EmptyState", () => {
  it("une phrase + l'action utile", () => {
    render(
      <EmptyState message="Aucune vente aujourd'hui" action={<a href="#v">Nouvelle vente</a>} />,
    );
    expect(screen.getByText("Aucune vente aujourd'hui")).toBeVisible();
    expect(screen.getByRole("link", { name: "Nouvelle vente" })).toBeVisible();
    expectRenderError(() => render(<EmptyState message="" />), "message");
  });
});

describe("Skeleton", () => {
  it("blocs border sans animation, libellé de chargement annoncé", () => {
    const { container } = render(<Skeleton lines={2} />);
    expect(screen.getByRole("status")).toHaveTextContent("Chargement…");
    const blocks = container.querySelectorAll('[aria-hidden="true"]');
    expect(blocks).toHaveLength(2);
    blocks.forEach((block) => {
      expect(block).toHaveClass("bg-border");
      expect(block.className).not.toMatch(/animate-/);
    });
  });

  it("refuse un nombre de lignes invalide", () => {
    expectRenderError(() => render(<Skeleton lines={0} />), "lines");
  });
});
