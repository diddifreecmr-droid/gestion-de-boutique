import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Package } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { MINUS, NBSP, THIN_NBSP, formatMoney } from "../format";
import {
  ActionTile,
  ActionTileGrid,
  Badge,
  KpiCard,
  ListCard,
  ListCardRow,
  SummaryCard,
} from "./index";
import { moneyParts } from "./cardClasses";
import { expectRenderError } from "./testUtils";

/** Testing Library ramène les espaces insécables à des espaces simples avant de comparer. */
const plain = (text: string) => text.replace(/\s+/g, " ");
const plainMoney = (amount: number) => plain(formatMoney(amount));

describe("KpiCard", () => {
  it("montant en --text-kpi, « FCFA » plus petit, variation en mots", () => {
    render(<KpiCard label="Ventes du jour" amount={2340000} detail="3 ventes" change={12} />);
    expect(screen.getByText(plain(`2${THIN_NBSP}340${THIN_NBSP}000`))).toHaveClass("text-kpi");
    expect(screen.getByText("FCFA")).toHaveClass("text-title-sm");
    expect(screen.getByText("3 ventes")).toBeVisible();
    expect(screen.getByText(plain(`+12${NBSP}% par rapport à hier`))).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("baisse, stabilité et référence personnalisée", () => {
    render(
      <>
        <KpiCard label="A" amount={1} change={-8} changeReference="par rapport à la veille" />
        <KpiCard label="B" amount={1} change={0} />
      </>,
    );
    expect(screen.getByText(plain(`${MINUS}8${NBSP}% par rapport à la veille`))).toBeVisible();
    expect(screen.getByText(plain(`0${NBSP}% par rapport à hier`))).toBeVisible();
  });

  it("toute la carte s'ouvre d'un appui", async () => {
    const onOpen = vi.fn();
    render(<KpiCard label="Marge du jour" amount={610000} onOpen={onOpen} />);
    await userEvent.click(screen.getByRole("button", { name: /Marge du jour/ }));
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it("refuse une variation non entière et un montant non entier", () => {
    expectRenderError(() => render(<KpiCard label="A" amount={1} change={1.5} />), "entier");
    expectRenderError(() => render(<KpiCard label="A" amount={1.5} />), "Montant invalide");
    expect(moneyParts(-5)).toEqual({ figure: `${MINUS}5`, unit: "FCFA" });
  });
});

describe("ListCard", () => {
  it("lignes de 64 px, montant formaté, pastille, ouverture", async () => {
    const onOpen = vi.fn();
    render(
      <ListCard label="Créances">
        <ListCardRow
          title="Moussa"
          subtitle="V-000124"
          amount={600000}
          badge={<Badge status="credit">Crédit</Badge>}
          onOpen={onOpen}
        />
        <ListCardRow title="Haojue" />
      </ListCard>,
    );
    const list = screen.getByRole("list", { name: "Créances" });
    expect(list).toHaveClass("divide-y", "divide-border");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText(plainMoney(600000))).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /Moussa/ }));
    expect(onOpen).toHaveBeenCalledOnce();
    expect(screen.getByText("Haojue").closest("span.min-h-16")).not.toBeNull();
  });

  it("élément annulé : barré en text-muted, sauf la pastille", () => {
    render(
      <ListCard label="Ventes">
        <ListCardRow
          title="V-000120"
          amount={1000}
          badge={<Badge status="danger">Annulée</Badge>}
          cancelled
        />
      </ListCard>,
    );
    expect(screen.getByText("V-000120")).toHaveClass("line-through", "text-text-muted");
    expect(screen.getByText("Annulée").parentElement).not.toHaveClass("line-through");
  });

  it("refuse un titre ou un nom de liste vide", () => {
    expectRenderError(() => render(<ListCard label="">x</ListCard>), "label");
    expectRenderError(() => render(<ListCardRow title="" />), "title");
  });
});

describe("ActionTile / SummaryCard", () => {
  it("tuile de 96 px : icône 32 px + mot", async () => {
    const onClick = vi.fn();
    render(
      <ActionTileGrid>
        <ActionTile icon={Package} label="Stock" onClick={onClick} />
      </ActionTileGrid>,
    );
    const tile = screen.getByRole("button", { name: "Stock" });
    expect(tile).toHaveClass("min-h-24");
    expect(tile.querySelector("svg")).toHaveClass("size-8");
    expect(tile.parentElement).toHaveClass("grid-cols-2");
    await userEvent.click(tile);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("le reste à payer est en credit-text et --text-amount", () => {
    render(
      <SummaryCard
        lines={[
          { label: "Total", amount: 800000 },
          { label: "Versé", amount: 200000 },
        ]}
        due={600000}
      />,
    );
    expect(screen.getByText("Reste à payer")).toHaveClass("text-credit-text");
    expect(screen.getByText(plainMoney(600000))).toHaveClass("text-credit-text", "text-amount");
    expect(screen.getByText(plainMoney(800000))).toHaveClass("text-right");
  });

  it("refuse un reste à payer négatif", () => {
    expectRenderError(() => render(<SummaryCard lines={[]} due={-1} />), "négatif");
  });
});
