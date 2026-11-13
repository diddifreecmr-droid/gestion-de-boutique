import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { Badge, CollapsibleSection, ListCard, ListCardDetailRow } from "./index";
import { expectRenderError } from "./testUtils";

describe("CollapsibleSection", () => {
  it("repliée par défaut : titre + résumé dans le bouton du titre, contenu non monté", async () => {
    const { container } = render(
      <CollapsibleSection title="Stock" summary="3 articles sous le seuil">
        <p>Valeur du stock</p>
      </CollapsibleSection>,
    );
    const heading = screen.getByRole("heading", { level: 2, name: /^Stock/ });
    const button = within(heading).getByRole("button");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveTextContent("Stock3 articles sous le seuil");
    expect(button).toHaveClass("min-h-(--control-lg)", "w-full");
    expect(screen.getByRole("region", { name: "Stock" })).toBeVisible();
    expect(screen.queryByText("Valeur du stock")).toBeNull();
    const panel = document.getElementById(button.getAttribute("aria-controls") ?? "");
    expect(panel).not.toBeNull();
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Valeur du stock")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await userEvent.click(button);
    expect(screen.queryByText("Valeur du stock")).toBeNull();
  });

  it("ouverte d'emblée, titre de niveau 3 ; un titre vide est refusé", () => {
    render(
      <CollapsibleSection title="Alertes" level={3} defaultOpen>
        <p>2 erreurs</p>
      </CollapsibleSection>,
    );
    expect(screen.getByRole("heading", { level: 3, name: "Alertes" })).toBeVisible();
    expect(screen.getByText("2 erreurs")).toBeVisible();
    expectRenderError(
      () =>
        render(
          <CollapsibleSection title=" ">
            <p>x</p>
          </CollapsibleSection>,
        ),
      "CollapsibleSection : title ne peut pas être vide",
    );
  });
});

describe("ListCardDetailRow", () => {
  it("ligne ≥ 64 px : titre, chiffre et pastille ; le détail se déplie sur place", async () => {
    const { container } = render(
      <ListCard label="Stock par article">
        <ListCardDetailRow
          title="Haojue HJ125-8"
          value="1"
          valueLabel="En stock"
          badge={<Badge status="warning">Stock bas</Badge>}
        >
          <p>Garoua : 1</p>
        </ListCardDetailRow>
      </ListCard>,
    );
    const row = screen.getByRole("button", { name: /Haojue HJ125-8/ });
    expect(row).toHaveTextContent("Haojue HJ125-8En stock1Stock bas");
    expect(row.firstElementChild).toHaveClass("min-h-16");
    expect(row).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Garoua : 1")).toBeNull();
    await userEvent.click(row);
    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Garoua : 1")).toBeVisible();
    expect(document.getElementById(row.getAttribute("aria-controls") ?? "")).toContainElement(
      screen.getByText("Garoua : 1"),
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("refuse un titre vide et un libellé de chiffre sans chiffre", () => {
    expectRenderError(
      () =>
        render(
          <ListCardDetailRow title="">
            <p>x</p>
          </ListCardDetailRow>,
        ),
      "ListCardDetailRow : title ne peut pas être vide",
    );
    expectRenderError(
      () =>
        render(
          <ListCardDetailRow title="A" valueLabel="En stock">
            <p>x</p>
          </ListCardDetailRow>,
        ),
      "ListCardDetailRow : valueLabel sans value",
    );
  });
});
