import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../../core/api/errors";
import { axeViolations } from "../../testing/axe";
import { saleReceipt } from "../../testing/receipts";
import { SHARE_OFFLINE, ShareButton } from "./ShareButton";

const source = () => Promise.resolve({ kind: "sale" as const, receipt: saleReceipt() });

describe("« Partager » le reçu en PDF (UC-VEN-04, RCP-05)", () => {
  it("module PDF chargé à l'appui, feuille de partage, puis confirmation", async () => {
    const share = vi.fn(() => Promise.resolve());
    const load = vi.fn(source);
    const user = userEvent.setup();
    const { container } = render(
      <ShareButton load={load} host={{ canShare: () => true, share, download: vi.fn() }} />,
    );
    expect(load).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Partager" }));
    expect(await screen.findByText("Reçu partagé.")).toBeVisible();
    expect(load).toHaveBeenCalledTimes(1);
    expect(share).toHaveBeenCalledTimes(1);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("sans Web Share : le PDF est téléchargé et l'écran le dit", async () => {
    const download = vi.fn();
    const user = userEvent.setup();
    render(<ShareButton load={source} host={{ download }} />);
    await user.click(screen.getByRole("button", { name: "Partager" }));
    expect(
      await screen.findByText(
        "Partage indisponible sur cet appareil : le PDF « recu-V-000130.pdf » a été téléchargé.",
      ),
    ).toBeVisible();
    expect((download.mock.calls[0] as unknown as [File])[0].name).toBe("recu-V-000130.pdf");
  });

  it("coupure ou refus du serveur : message, rien n'est partagé", async () => {
    const download = vi.fn();
    const user = userEvent.setup();
    const offline = () => Promise.reject(new NetworkError("coupure"));
    const { unmount } = render(<ShareButton load={offline} host={{ download }} />);
    await user.click(screen.getByRole("button", { name: "Partager" }));
    expect(await screen.findByText(SHARE_OFFLINE)).toBeVisible();
    unmount();
    const refused = () => Promise.reject(new ApiError(404, "NOT_FOUND", "Élément introuvable"));
    render(<ShareButton load={refused} host={{ download }} />);
    await user.click(screen.getByRole("button", { name: "Partager" }));
    expect(
      await screen.findByText("Reçu indisponible : Élément introuvable (NOT_FOUND)."),
    ).toBeVisible();
    expect(download).not.toHaveBeenCalled();
  });
});
