import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { House, Package, ShoppingCart } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { ActionBar, BottomNav, MAX_NAV_ITEMS, TopBar, type NavItem } from "./index";
import { alertBadgeText, alertsLabel } from "./navigation";
import { expectRenderError } from "./testUtils";

const item = (key: string, label = key): NavItem => ({ key, label, icon: House, href: `#${key}` });
const ITEMS: NavItem[] = [
  { key: "home", label: "Accueil", icon: House, href: "/" },
  { key: "sales", label: "Ventes", icon: ShoppingCart, href: "/ventes" },
  { key: "stock", label: "Stock", icon: Package, href: "/stock" },
];

describe("TopBar", () => {
  it("56 px, nom de boutique cliquable, cloche avec compteur et libellé", async () => {
    const onTitle = vi.fn();
    const onAlerts = vi.fn();
    render(
      <TopBar
        title="Motos Garoua"
        onTitleClick={onTitle}
        alertCount={3}
        onAlertsClick={onAlerts}
      />,
    );
    expect(screen.getByRole("banner")).toHaveClass("min-h-(--control-lg)");
    await userEvent.click(screen.getByRole("button", { name: "Motos Garoua" }));
    expect(onTitle).toHaveBeenCalledOnce();
    const bell = screen.getByRole("button", { name: "Alertes, 3 nouvelles" });
    expect(bell).toHaveClass("min-h-(--control-md)", "min-w-(--control-md)");
    expect(bell).toHaveTextContent("3");
    await userEvent.click(bell);
    expect(onAlerts).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Retour" })).toBeNull();
  });

  it("écran de détail : retour, titre simple, pas de compteur à zéro", async () => {
    const onBack = vi.fn();
    render(
      <TopBar title="Nouvelle vente" onBack={onBack} alertCount={0} onAlertsClick={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Retour" }));
    expect(onBack).toHaveBeenCalledOnce();
    expect(screen.getByText("Nouvelle vente").tagName).toBe("P");
    expect(screen.getByRole("button", { name: "Alertes, aucune nouvelle" })).toHaveTextContent("");
  });

  it("textes du compteur et refus d'un compteur invalide", () => {
    expect(alertBadgeText(120)).toBe("99+");
    expect(alertsLabel(1)).toBe("Alertes, 1 nouvelle");
    expectRenderError(
      () => render(<TopBar title="X" alertCount={-1} onAlertsClick={vi.fn()} />),
      "alertCount",
    );
  });
});

describe("BottomNav", () => {
  it("icône + mot, 64 px, entrée active primary + trait 3 px + aria-current", () => {
    render(<BottomNav items={ITEMS} activeKey="sales" />);
    const nav = screen.getByRole("navigation", { name: "Navigation principale" });
    expect(nav).toHaveClass("fixed", "bottom-0", "safe-bottom-0");
    const active = screen.getByRole("link", { name: "Ventes" });
    expect(active).toHaveAttribute("aria-current", "page");
    expect(active).toHaveClass("h-16", "border-t-3", "border-primary", "text-primary");
    const other = screen.getByRole("link", { name: "Stock" });
    expect(other).not.toHaveAttribute("aria-current");
    expect(other).toHaveClass("border-transparent", "text-text-muted");
  });

  it("laisse le routeur intercepter la navigation", async () => {
    const onNavigate = vi.fn((_: NavItem, event: { preventDefault: () => void }) => {
      event.preventDefault();
    });
    render(<BottomNav items={ITEMS} activeKey={null} fixed={false} onNavigate={onNavigate} />);
    await userEvent.click(screen.getByRole("link", { name: "Stock" }));
    expect(onNavigate.mock.calls[0]?.[0]).toBe(ITEMS[2]);
    expect(screen.getByRole("navigation")).not.toHaveClass("fixed");
  });

  it(`lève une erreur explicite au-delà de ${String(MAX_NAV_ITEMS)} entrées (fail-fast)`, () => {
    const six = ["a", "b", "c", "d", "e", "f"].map((key) => item(key));
    expectRenderError(() => render(<BottomNav items={six} activeKey={null} />), "5 au plus");
    expect(() => render(<BottomNav items={six.slice(0, 5)} activeKey="a" />)).not.toThrow();
  });

  it("refuse aucune entrée, des clés en double, une entrée active inconnue, un mot vide", () => {
    expectRenderError(() => render(<BottomNav items={[]} activeKey={null} />), "au moins une");
    expectRenderError(
      () => render(<BottomNav items={[item("a"), item("a")]} activeKey={null} />),
      "en double",
    );
    expectRenderError(() => render(<BottomNav items={ITEMS} activeKey="x" />), "n'existe pas");
    expectRenderError(
      () => render(<BottomNav items={[item("a", " ")]} activeKey={null} />),
      "label",
    );
  });
});

describe("ActionBar", () => {
  it("fixée en bas, surface + --shadow-sheet + marge de sécurité", () => {
    const { container } = render(
      <ActionBar summary="Total 780 000 FCFA">
        <button type="button">Valider</button>
      </ActionBar>,
    );
    expect(container.firstElementChild).toHaveClass(
      "fixed",
      "bottom-0",
      "bg-surface",
      "shadow-sheet",
      "safe-bottom-4",
    );
    expect(screen.getByText("Total 780 000 FCFA")).toBeVisible();
  });

  it("peut s'afficher dans le flux", () => {
    const { container } = render(
      <ActionBar fixed={false}>
        <span>Action</span>
      </ActionBar>,
    );
    expect(container.firstElementChild).not.toHaveClass("fixed");
  });
});
