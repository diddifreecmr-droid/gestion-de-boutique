import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Switch } from "./index";
import { expectRenderError } from "./testUtils";

function Controlled({ hint }: { hint?: string }) {
  const [on, setOn] = useState(false);
  return (
    <Switch
      label="Créances"
      checked={on}
      onChange={setOn}
      {...(hint === undefined ? {} : { hint })}
    />
  );
}

describe("Switch", () => {
  it("motif « switch » : nom, état en mots et en aria-checked, ligne de 56 px", async () => {
    const user = userEvent.setup();
    render(<Controlled />);
    const toggle = screen.getByRole("switch", { name: "Créances" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle).toHaveClass("min-h-(--control-lg)", "focus-visible:outline-solid");
    expect(toggle).toHaveTextContent("Désactivé");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-checked", "true");
    expect(toggle).toHaveTextContent("Activé");
    await user.keyboard(" ");
    expect(toggle).toHaveAttribute("aria-checked", "false");
  });

  it("la phrase d'aide est reliée par aria-describedby", () => {
    render(<Controlled hint="Nécessite Transferts." />);
    expect(screen.getByRole("switch", { name: "Créances" })).toHaveAccessibleDescription(
      "Nécessite Transferts.",
    );
  });

  it("libellé vide : erreur explicite", () => {
    expectRenderError(
      () => render(<Switch label=" " checked={false} onChange={() => undefined} />),
      "Switch : label ne peut pas être vide",
    );
  });
});
