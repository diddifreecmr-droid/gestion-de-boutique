import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { THIN_NBSP } from "../format";
import { AmountField, MAX_AMOUNT_DIGITS } from "./index";
import {
  caretAfterDigits,
  digitsBefore,
  digitsOf,
  formatAmountInput,
  parseAmountInput,
} from "./amountInput";
import { expectRenderError } from "./testUtils";

function Controlled({
  initial = null,
  spy,
}: {
  initial?: number | null;
  spy?: (v: number | null) => void;
}) {
  const [value, setValue] = useState<number | null>(initial);
  return (
    <>
      <AmountField
        label="Prix"
        value={value}
        onChange={(next) => {
          spy?.(next);
          setValue(next);
        }}
      />
      <output data-testid="value">{value === null ? "null" : String(value)}</output>
    </>
  );
}

const g = (text: string) => text.replaceAll(" ", THIN_NBSP);

describe("amountInput", () => {
  it("lit les chiffres seulement, jamais NaN", () => {
    expect(digitsOf("0 07a8")).toBe("78");
    expect(digitsOf("000")).toBe("0");
    expect(parseAmountInput("")).toEqual({ ok: true, value: null });
    expect(parseAmountInput("abc")).toEqual({ ok: true, value: null });
    expect(parseAmountInput(g("780 000"))).toEqual({ ok: true, value: 780000 });
    expect(parseAmountInput("9".repeat(MAX_AMOUNT_DIGITS + 1))).toEqual({ ok: false });
  });

  it("formate avec le séparateur de milliers et refuse une valeur invalide", () => {
    expect(formatAmountInput(null)).toBe("");
    expect(formatAmountInput(1250000)).toBe(g("1 250 000"));
    expect(() => formatAmountInput(Number.NaN)).toThrow("valeur invalide");
    expect(() => formatAmountInput(-5)).toThrow("entier positif");
    expect(() => formatAmountInput(1.5)).toThrow("valeur invalide");
  });

  it("calcule la position du curseur en chiffres", () => {
    expect(digitsBefore(g("78 000"), 4)).toBe(3);
    expect(caretAfterDigits(g("780 000"), 0)).toBe(0);
    expect(caretAfterDigits(g("780 000"), 4)).toBe(5);
    expect(caretAfterDigits("12", 5)).toBe(2);
  });
});

describe("AmountField", () => {
  it("clavier numérique, suffixe FCFA relié, valeur en gras lead", () => {
    render(<AmountField label="Prix" value={780000} onChange={() => undefined} />);
    const input = screen.getByLabelText("Prix");
    expect(input).toHaveAttribute("inputmode", "numeric");
    expect(input).toHaveValue(g("780 000"));
    expect(input).toHaveAccessibleDescription("FCFA");
    expect(input).toHaveClass("text-lead", "font-bold");
  });

  it("insère le séparateur pendant la frappe et expose un entier", async () => {
    const spy = vi.fn();
    render(<Controlled spy={spy} />);
    const input = screen.getByLabelText("Prix");
    await userEvent.type(input, "1250000");
    expect(input).toHaveValue(g("1 250 000"));
    expect(screen.getByTestId("value")).toHaveTextContent("1250000");
    expect(spy).toHaveBeenLastCalledWith(1250000);
  });

  it("ignore les lettres et rend null quand on vide le champ", async () => {
    const spy = vi.fn();
    render(<Controlled initial={45} spy={spy} />);
    const input = screen.getByLabelText("Prix");
    await userEvent.type(input, "a");
    expect(spy).toHaveBeenLastCalledWith(45);
    await userEvent.clear(input);
    expect(spy).toHaveBeenLastCalledWith(null);
    expect(screen.getByTestId("value")).toHaveTextContent("null");
  });

  it("garde le curseur après le même chiffre quand un séparateur apparaît", async () => {
    render(<Controlled initial={78000} />);
    const input = screen.getByLabelText<HTMLInputElement>("Prix");
    await userEvent.click(input);
    input.setSelectionRange(2, 2);
    await userEvent.keyboard("0");
    expect(input).toHaveValue(g("780 000"));
    expect(input.selectionStart).toBe(3);
  });

  it("refuse la frappe au-delà de 15 chiffres", async () => {
    const spy = vi.fn();
    const max = Number("9".repeat(MAX_AMOUNT_DIGITS));
    render(<Controlled initial={max} spy={spy} />);
    await userEvent.type(screen.getByLabelText("Prix"), "9");
    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByTestId("value")).toHaveTextContent(String(max));
  });

  it("erreur affichée et refus d'une valeur NaN (fail-fast)", () => {
    render(
      <AmountField
        label="Total"
        value={null}
        onChange={() => undefined}
        error="Le prix est vide"
      />,
    );
    expect(screen.getByLabelText("Total")).toHaveAccessibleDescription("FCFA Le prix est vide");
    expectRenderError(
      () => render(<AmountField label="X" value={Number.NaN} onChange={() => undefined} />),
      "valeur invalide",
    );
  });
});
