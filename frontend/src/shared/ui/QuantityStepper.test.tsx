import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { QuantityStepper } from "./index";
import { expectRenderError } from "./testUtils";

function Controlled({ initial, available }: { initial: number; available?: number }) {
  const [value, setValue] = useState(initial);
  return (
    <QuantityStepper
      label="Quantité"
      value={value}
      onChange={setValue}
      {...(available === undefined ? {} : { available })}
    />
  );
}

const minus = () => screen.getByRole("button", { name: "Quantité : moins un" });
const plus = () => screen.getByRole("button", { name: "Quantité : plus un" });

describe("QuantityStepper", () => {
  it("boutons de 48 px, valeur reliée au libellé, stock disponible dessous", () => {
    render(<Controlled initial={1} available={4} />);
    expect(minus()).toHaveClass("size-(--control-md)");
    expect(plus()).toHaveClass("size-(--control-md)");
    expect(screen.getByLabelText("Quantité")).toHaveTextContent("1");
    expect(screen.getByText("Stock disponible : 4")).toHaveClass("text-text-muted");
  });

  it("inline : libellé et boutons sur la même ligne, aide dessous, toujours reliés", () => {
    render(
      <QuantityStepper label="Quantité" value={2} onChange={vi.fn()} hint="Par pièce" inline />,
    );
    const output = screen.getByLabelText("Quantité");
    expect(output).toHaveTextContent("2");
    expect(output).toHaveAccessibleDescription("Par pièce");
    const row = screen.getByText("Quantité").parentElement;
    expect(row).toHaveClass("flex-wrap", "justify-between");
    expect(row).toContainElement(minus());
    expect(row).not.toContainElement(screen.getByText("Par pièce"));
  });

  it("augmente et diminue dans les bornes", async () => {
    render(<Controlled initial={3} available={4} />);
    await userEvent.click(plus());
    expect(screen.getByLabelText("Quantité")).toHaveTextContent("4");
    expect(plus()).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(plus());
    expect(screen.getByLabelText("Quantité")).toHaveTextContent("4");
    await userEvent.click(minus());
    expect(screen.getByLabelText("Quantité")).toHaveTextContent("3");
  });

  it("bloque sous le minimum (1 par défaut) sans perdre le focus", async () => {
    const onChange = vi.fn();
    render(<QuantityStepper label="Quantité" value={1} onChange={onChange} />);
    expect(minus()).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(minus());
    expect(onChange).not.toHaveBeenCalled();
    expect(minus()).toHaveFocus();
    expect(plus()).not.toHaveAttribute("aria-disabled");
  });

  it("la borne la plus basse entre max et available s'applique", () => {
    render(<QuantityStepper label="Quantité" value={2} onChange={vi.fn()} max={2} available={9} />);
    expect(plus()).toHaveAttribute("aria-disabled", "true");
  });

  it("refuse une valeur hors bornes, non entière ou des bornes impossibles", () => {
    const noop = () => undefined;
    expectRenderError(
      () => render(<QuantityStepper label="Q" value={5} onChange={noop} available={4} />),
      "hors des bornes",
    );
    expectRenderError(
      () => render(<QuantityStepper label="Q" value={1.5} onChange={noop} />),
      "value doit être un entier",
    );
    expectRenderError(
      () => render(<QuantityStepper label="Q" value={1} onChange={noop} min={3} max={2} />),
      "bornes impossibles",
    );
  });
});
