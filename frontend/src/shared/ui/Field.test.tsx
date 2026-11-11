import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Field, TextField } from "./index";
import { expectRenderError } from "./testUtils";

describe("Field / TextField", () => {
  it("relie le libellé au-dessus, l'aide et le champ", () => {
    render(<TextField label="Nom du client" hint="Facultatif" />);
    const input = screen.getByLabelText("Nom du client");
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveAccessibleDescription("Facultatif");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input.parentElement).toHaveClass(
      "min-h-(--control-md)",
      "border-border-strong",
      "focus-within:outline-solid",
    );
  });

  it("transmet la saisie", async () => {
    const onChange = vi.fn();
    render(<TextField label="Couleur" onChange={onChange} />);
    await userEvent.type(screen.getByLabelText("Couleur"), "Rouge");
    expect(onChange).toHaveBeenCalledTimes(5);
  });

  it("erreur : message relié, icône, bordure danger, région aria-live", () => {
    render(<TextField label="Prix" error="Le prix est vide" id="prix" />);
    const input = screen.getByLabelText("Prix");
    expect(input).toHaveAttribute("id", "prix");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Le prix est vide");
    expect(input.parentElement).toHaveClass("border-danger", "ring-danger");
    const message = screen.getByText("Le prix est vide").closest("p");
    expect(message).toHaveClass("text-danger-text");
    expect(message?.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(message?.parentElement).toHaveAttribute("aria-live", "polite");
  });

  it("garde la région aria-live même sans erreur (annonce à l'apparition)", () => {
    const { container } = render(<TextField label="Prix" />);
    expect(container.querySelector('[aria-live="polite"]')).toBeEmptyDOMElement();
  });

  it("ajoute les descriptions supplémentaires et le pied", () => {
    render(
      <>
        <span id="unite">FCFA</span>
        <Field label="Montant" describedBy="unite" footer={<p>Pied</p>}>
          {(control) => <input {...control} />}
        </Field>
      </>,
    );
    expect(screen.getByLabelText("Montant")).toHaveAccessibleDescription("FCFA");
    expect(screen.getByText("Pied")).toBeVisible();
  });

  it("refuse un libellé vide ou une erreur vide (fail-fast)", () => {
    expectRenderError(() => render(<TextField label=" " />), "label ne peut pas être vide");
    expectRenderError(() => render(<TextField label="Prix" error="" />), "error ne peut pas");
  });
});
