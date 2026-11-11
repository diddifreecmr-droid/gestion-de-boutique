import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog, REASON_REQUIRED } from "./index";
import { focusableIn } from "./useFocusTrap";
import { expectRenderError } from "./testUtils";

interface HarnessProps {
  requireReason?: boolean;
  onConfirm?: (reason: string | null) => void;
}

function Harness({ requireReason = false, onConfirm = vi.fn() }: HarnessProps) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
        }}
      >
        Ouvrir
      </button>
      <ConfirmDialog
        open={open}
        title="Annuler la vente ?"
        confirmLabel="Annuler la vente"
        requireReason={requireReason}
        onConfirm={(reason) => {
          onConfirm(reason);
          setOpen(false);
        }}
        onCancel={() => {
          setOpen(false);
        }}
      >
        La vente reste visible, barrée.
      </ConfirmDialog>
    </>
  );
}

async function openDialog() {
  await userEvent.click(screen.getByRole("button", { name: "Ouvrir" }));
  return screen.getByRole("dialog", { name: "Annuler la vente ?" });
}

describe("ConfirmDialog", () => {
  it("fermé : rien n'est rendu", () => {
    render(<Harness />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("modale nommée et décrite, feuille du bas, focus sur « Retour »", async () => {
    render(<Harness />);
    const dialog = await openDialog();
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleDescription("La vente reste visible, barrée.");
    expect(dialog).toHaveClass("rounded-t-lg", "shadow-sheet", "safe-bottom-4");
    const back = screen.getByRole("button", { name: "Retour" });
    expect(back).toHaveFocus();
    expect(back).toHaveClass("border-border-strong");
    const confirm = screen.getByRole("button", { name: "Annuler la vente" });
    expect(confirm).toHaveClass("bg-danger");
    expect(focusableIn(dialog).at(-1)).toBe(confirm);
  });

  it("piège le focus (Tab / Maj+Tab bouclent)", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await openDialog();
    await user.tab();
    expect(screen.getByRole("button", { name: "Annuler la vente" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Retour" })).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Annuler la vente" })).toHaveFocus();
  });

  it("Échap ferme et rend le focus au bouton d'ouverture", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await openDialog();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Ouvrir" })).toHaveFocus();
  });

  it("sans motif demandé : confirme avec null", async () => {
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} />);
    await openDialog();
    await userEvent.click(screen.getByRole("button", { name: "Annuler la vente" }));
    expect(onConfirm).toHaveBeenCalledWith(null);
  });

  it("motif obligatoire : refuse un motif vide, puis transmet le motif nettoyé", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<Harness requireReason onConfirm={onConfirm} />);
    await openDialog();
    const reason = screen.getByLabelText("Motif");
    expect(reason).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Annuler la vente" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(reason).toHaveAccessibleDescription(REASON_REQUIRED);
    expect(reason).toHaveFocus();
    await user.type(reason, "  erreur de prix ");
    expect(reason).not.toHaveAttribute("aria-invalid");
    await user.click(screen.getByRole("button", { name: "Annuler la vente" }));
    expect(onConfirm).toHaveBeenCalledWith("erreur de prix");
  });

  it("refuse un titre vide (fail-fast)", () => {
    const noop = () => undefined;
    expectRenderError(
      () =>
        render(<ConfirmDialog open title="" confirmLabel="OK" onConfirm={noop} onCancel={noop} />),
      "title",
    );
  });
});
