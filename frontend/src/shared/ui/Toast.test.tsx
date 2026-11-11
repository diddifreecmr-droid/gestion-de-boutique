import { act, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TOAST_SUCCESS_MS, ToastProvider, useToast, type ToastApi } from "./index";
import { expectRenderError } from "./testUtils";

let api: ToastApi | null = null;
function toasts(): ToastApi {
  if (api === null) throw new Error("ToastProvider non monté");
  return api;
}

describe("Toast / ToastProvider", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api = renderHook(() => useToast(), { wrapper: ToastProvider }).result.current;
  });
  afterEach(() => {
    vi.useRealTimers();
    api = null;
  });

  it("succès : region status, success/blanc, 48 px, disparaît après 4 s", () => {
    act(() => {
      toasts().show({ tone: "success", message: "Vente enregistrée" });
    });
    const message = screen.getByText("Vente enregistrée");
    expect(screen.getByRole("status")).toContainElement(message);
    expect(message.parentElement).toHaveClass(
      "bg-success",
      "text-on-primary",
      "min-h-(--control-md)",
    );
    act(() => {
      vi.advanceTimersByTime(TOAST_SUCCESS_MS - 1);
    });
    expect(screen.getByText("Vente enregistrée")).toBeVisible();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.queryByText("Vente enregistrée")).toBeNull();
  });

  it("erreur : region alert, danger, reste jusqu'à « Fermer »", async () => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    act(() => {
      toasts().show({ tone: "error", message: "Échec de l'envoi" });
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Échec de l'envoi");
    expect(screen.getByText("Échec de l'envoi").parentElement).toHaveClass("bg-danger");
    act(() => {
      vi.advanceTimersByTime(TOAST_SUCCESS_MS * 10);
    });
    expect(screen.getByText("Échec de l'envoi")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Fermer" }));
    expect(screen.queryByText("Échec de l'envoi")).toBeNull();
  });

  it("dismiss par code, y compris un succès avant son délai", () => {
    let id = 0;
    act(() => {
      id = toasts().show({ tone: "success", message: "Reçu partagé" });
    });
    act(() => {
      toasts().dismiss(id);
    });
    expect(screen.queryByText("Reçu partagé")).toBeNull();
  });

  it("refuse un message vide", () => {
    expect(() => toasts().show({ tone: "error", message: " " })).toThrow("message");
  });
});

describe("useToast hors fournisseur", () => {
  it("lève une erreur explicite (fail-fast)", () => {
    expectRenderError(() => renderHook(() => useToast()), "sous un <ToastProvider>");
  });
});
