import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { SegmentedControl } from "./index";
import { expectRenderError } from "./testUtils";

type Mode = "meter" | "piece";
const OPTIONS = [
  { value: "meter", label: "Au mètre" },
  { value: "piece", label: "À la pièce" },
] as const;

function Controlled() {
  const [value, setValue] = useState<Mode>("meter");
  return <SegmentedControl label="Vente" options={OPTIONS} value={value} onChange={setValue} />;
}

const radio = (name: string) => screen.getByRole("radio", { name });

describe("SegmentedControl (design-system § 7.5)", () => {
  it("radiogroup nommé, segments de 56 px, actif primary-soft + Check ; axe", async () => {
    const { container } = render(<Controlled />);
    expect(screen.getByRole("radiogroup", { name: "Vente" })).toBeVisible();
    const meter = radio("Au mètre");
    expect(meter).toHaveAttribute("aria-checked", "true");
    expect(meter).toHaveClass("min-h-(--control-lg)", "bg-primary-soft", "border-primary");
    expect(meter.querySelectorAll("svg")).toHaveLength(1);
    expect(radio("À la pièce").querySelector("svg")).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("un appui ou les flèches changent le segment ; une seule tabulation", async () => {
    const user = userEvent.setup();
    render(<Controlled />);
    await user.click(radio("À la pièce"));
    expect(radio("À la pièce")).toHaveAttribute("aria-checked", "true");
    expect(radio("Au mètre")).toHaveAttribute("tabindex", "-1");
    await user.keyboard("{ArrowRight}");
    expect(radio("Au mètre")).toHaveFocus();
    expect(radio("Au mètre")).toHaveAttribute("aria-checked", "true");
  });

  it("fail-fast : un seul segment, ou une valeur hors liste", () => {
    expectRenderError(
      () =>
        render(
          <SegmentedControl label="Vente" options={[OPTIONS[0]]} value="meter" onChange={noop} />,
        ),
      "deux segments au moins",
    );
    expectRenderError(
      () =>
        render(
          <SegmentedControl label="Vente" options={OPTIONS} value={"yard" as Mode} onChange={noop} />,
        ),
      "n'est pas un segment",
    );
  });
});

function noop() {
  // Rien à faire : le rendu échoue avant tout choix.
}
