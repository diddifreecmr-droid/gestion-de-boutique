import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Disclosure, SearchField } from "./index";

describe("Disclosure", () => {
  it("« Plus de détails » replié par défaut, s'ouvre et se referme", async () => {
    render(
      <Disclosure>
        <p>Châssis</p>
      </Disclosure>,
    );
    const button = screen.getByRole("button", { name: "Plus de détails" });
    expect(button).toHaveClass("w-full", "bg-transparent", "min-h-(--control-md)");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Châssis")).not.toBeVisible();
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Châssis")).toBeVisible();
    expect(button.getAttribute("aria-controls")).toBe(
      screen.getByText("Châssis").parentElement?.id,
    );
    await userEvent.click(button);
    expect(screen.getByText("Châssis")).not.toBeVisible();
  });

  it("peut être ouvert d'emblée avec un autre libellé", () => {
    render(
      <Disclosure label="Options" defaultOpen>
        <p>Client</p>
      </Disclosure>,
    );
    expect(screen.getByRole("button", { name: "Options" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText("Client")).toBeVisible();
  });
});

function Search({ initial }: { initial: string }) {
  const [value, setValue] = useState(initial);
  return <SearchField label="Article" value={value} onChange={setValue} />;
}

describe("SearchField", () => {
  it("loupe, saisie dès la première lettre, pas de bouton Effacer à vide", async () => {
    render(<Search initial="" />);
    const input = screen.getByLabelText("Article");
    expect(input).toHaveAttribute("inputmode", "search");
    expect(screen.queryByRole("button", { name: "Effacer" })).toBeNull();
    await userEvent.type(input, "H");
    expect(input).toHaveValue("H");
  });

  it("« Effacer » (icône + mot, 48 px) vide le champ et rend le focus", async () => {
    render(<Search initial="Haojue" />);
    const clear = screen.getByRole("button", { name: "Effacer" });
    expect(clear).toHaveClass("min-h-(--control-md)");
    await userEvent.click(clear);
    const input = screen.getByLabelText("Article");
    expect(input).toHaveValue("");
    expect(input).toHaveFocus();
  });
});
