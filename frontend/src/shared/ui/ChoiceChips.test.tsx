import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Banknote } from "lucide-react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { ChoiceChips, type ChoiceOption } from "./index";
import { expectRenderError } from "./testUtils";

type Mode = "cash" | "orange" | "mtn";
const OPTIONS: ChoiceOption<Mode>[] = [
  { value: "cash", label: "Espèces", icon: Banknote },
  { value: "orange", label: "Orange Money" },
  { value: "mtn", label: "MTN MoMo" },
];

function Controlled({ initial }: { initial: Mode | null }) {
  const [value, setValue] = useState<Mode | null>(initial);
  return <ChoiceChips label="Paiement" options={OPTIONS} value={value} onChange={setValue} />;
}

describe("ChoiceChips", () => {
  it("radiogroup nommé, choix de 56 px, 2 par ligne", () => {
    render(<Controlled initial="cash" />);
    const group = screen.getByRole("radiogroup", { name: "Paiement" });
    expect(group).toHaveClass("grid-cols-2");
    const cash = screen.getByRole("radio", { name: "Espèces" });
    expect(cash).toHaveClass("min-h-(--control-lg)", "focus-visible:outline-solid");
    expect(cash).toHaveAttribute("aria-checked", "true");
  });

  it("actif : primary-soft, bordure 2 px primary et icône Check", () => {
    render(<Controlled initial="orange" />);
    const active = screen.getByRole("radio", { name: "Orange Money" });
    expect(active).toHaveClass("bg-primary-soft", "border-primary", "ring-1", "ring-primary");
    expect(active.querySelectorAll("svg")).toHaveLength(1);
    expect(screen.getByRole("radio", { name: "MTN MoMo" }).querySelector("svg")).toBeNull();
  });

  it("un appui choisit ; une seule tabulation ; les flèches bouclent", async () => {
    const user = userEvent.setup();
    render(<Controlled initial={null} />);
    const [cash, orange, mtn] = screen.getAllByRole("radio");
    expect(cash).toHaveAttribute("tabindex", "0");
    expect(orange).toHaveAttribute("tabindex", "-1");
    await user.click(screen.getByRole("radio", { name: "MTN MoMo" }));
    expect(mtn).toHaveAttribute("aria-checked", "true");
    await user.keyboard("{ArrowRight}");
    expect(cash).toHaveAttribute("aria-checked", "true");
    expect(cash).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(mtn).toHaveFocus();
    await user.keyboard("{ArrowUp}{ArrowDown}{Enter}a");
    expect(mtn).toHaveAttribute("aria-checked", "true");
  });

  it("refuse les listes vides, les doublons et une valeur inconnue (fail-fast)", () => {
    const noop = () => undefined;
    expectRenderError(
      () => render(<ChoiceChips label="P" options={[]} value={null} onChange={noop} />),
      "options ne peut pas être vide",
    );
    expectRenderError(
      () =>
        render(
          <ChoiceChips
            label="P"
            options={[OPTIONS[0], OPTIONS[0]].filter((o) => o !== undefined)}
            value={null}
            onChange={noop}
          />,
        ),
      "valeurs en double",
    );
    expectRenderError(
      () => render(<ChoiceChips label="P" options={OPTIONS} value={"x" as Mode} onChange={noop} />),
      "n'est pas une option",
    );
  });
});
