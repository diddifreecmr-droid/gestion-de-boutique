import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../core/api/errors";
import type { AttachmentsGateway } from "../../../core/gateways/attachmentsContract";
import { AttachmentsContext } from "../../../core/gateways/httpAttachments";
import { ShopAdminContext } from "../../../core/gateways/httpShopAdmin";
import type { ShopAdminGateway, ShopSettings } from "../../../core/gateways/shopAdminContract";
import { ShopLogoContext } from "../../../core/profile/shopLogoContext";
import { ToastProvider } from "../../../shared/ui";
import { attachment, fakeCodec, pdfFile, photoFile } from "../../../testing/attachments";
import { axeViolations } from "../../../testing/axe";
import { SHOP_A } from "../../../testing/fakeApi";
import { settings } from "../../../testing/shopSettingsApi";
import { LogoSection } from "./LogoSection";

const LOGO_ID = "01890a5d-ac96-774b-bcce-b302099a9077";

function setup(current: ShopSettings, src: string | null = null) {
  const upload = vi.fn<AttachmentsGateway["upload"]>(() =>
    Promise.resolve(attachment({ id: LOGO_ID, owner_type: "shop", owner_id: null, kind: "photo" })),
  );
  const updateSettings = vi.fn<ShopAdminGateway["updateSettings"]>((_shop, patch) =>
    Promise.resolve(settings({ logo_attachment_id: patch.logo_attachment_id ?? null, version: 4 })),
  );
  const replace = vi.fn();
  const onSaved = vi.fn();
  const codec = fakeCodec(30_000);
  const attachments = { upload } as unknown as AttachmentsGateway;
  const admin = { updateSettings } as unknown as ShopAdminGateway;
  const view = render(
    <ToastProvider>
      <AttachmentsContext.Provider value={attachments}>
        <ShopAdminContext.Provider value={admin}>
          <ShopLogoContext.Provider value={{ src, replace }}>
            <LogoSection shopId={SHOP_A} settings={current} onSaved={onSaved} codec={codec} />
          </ShopLogoContext.Provider>
        </ShopAdminContext.Provider>
      </AttachmentsContext.Provider>
    </ToastProvider>,
  );
  return { ...view, upload, updateSettings, replace, onSaved, codec, user: userEvent.setup({ applyAccept: false }) };
}

beforeEach(() => {
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:logo") }));
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Logo de la boutique (réglages, specs § 15.1)", () => {
  it("sans logo : initiales ; envoi réduit à 512 px (PNG), désigné, barre du haut mise à jour ; axe", async () => {
    const t = setup(settings());
    expect(screen.getByRole("img", { name: "Logo générique (initiales)" })).toHaveTextContent("MG");
    expect(await axeViolations(t.container)).toEqual([]);
    await t.user.upload(screen.getByLabelText("Envoyer le logo"), photoFile());
    expect(await screen.findByText("Logo de la boutique : enregistré.")).toBeVisible();
    expect(t.codec.calls).toEqual([512]);
    const sent = t.upload.mock.calls[0]?.[1];
    expect(sent).toMatchObject({ ownerType: "shop", ownerId: null, kind: "photo" });
    expect(sent?.fileName).toBe("IMG_0001.png");
    expect(t.updateSettings).toHaveBeenCalledWith(SHOP_A, {
      logo_attachment_id: LOGO_ID,
      version: 3,
    });
    expect(t.onSaved).toHaveBeenCalledOnce();
    expect(t.replace).toHaveBeenCalledWith("blob:logo");
  });

  it("logo réglé : aperçu, « Retirer le logo » désigne `null` et remet les initiales", async () => {
    const t = setup(settings({ logo_attachment_id: LOGO_ID }), "https://api.test/logo.png");
    expect(screen.getByRole("img", { name: "Logo de la boutique" })).toHaveAttribute(
      "src",
      "https://api.test/logo.png",
    );
    await t.user.click(screen.getByRole("button", { name: "Retirer le logo" }));
    expect(await screen.findByText(/Logo retiré/)).toBeVisible();
    expect(t.updateSettings).toHaveBeenCalledWith(SHOP_A, { logo_attachment_id: null, version: 3 });
    expect(t.replace).toHaveBeenCalledWith(null);
    expect(screen.getByRole("button", { name: "Changer le logo" })).toBeVisible();
  });

  it("un PDF est refusé avant l'envoi ; un refus du serveur s'affiche, rien n'est remplacé", async () => {
    const t = setup(settings());
    await t.user.upload(screen.getByLabelText("Envoyer le logo"), pdfFile());
    expect(await screen.findByText("Le logo est une image : photo JPG ou PNG.")).toBeVisible();
    expect(t.upload).not.toHaveBeenCalled();
    t.updateSettings.mockRejectedValueOnce(new ApiError(403, "FORBIDDEN", "Réservé au gérant"));
    await t.user.upload(screen.getByLabelText("Envoyer le logo"), photoFile());
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(t.replace).not.toHaveBeenCalled();
  });
});
