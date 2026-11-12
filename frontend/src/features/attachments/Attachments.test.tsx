import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../../core/api/errors";
import type { AttachmentsGateway } from "../../core/gateways/attachmentsContract";
import { AttachmentsContext } from "../../core/gateways/httpAttachments";
import { attachment, CONTENT_URL, fakeCodec, photoFile } from "../../testing/attachments";
import { axeViolations } from "../../testing/axe";
import { SHOP_A } from "../../testing/fakeApi";
import { STORAGE_DOWN } from "./attachmentErrors";
import { AttachmentUpload } from "./AttachmentUpload";
import { AttachmentView } from "./AttachmentView";

function fakeGateway(overrides: Partial<AttachmentsGateway> = {}): AttachmentsGateway {
  return {
    upload: vi.fn(() => Promise.resolve(attachment())),
    link: vi.fn(() =>
      Promise.resolve({
        url: CONTENT_URL,
        expiresAt: new Date(),
        mime: "image/jpeg" as const,
        kind: "id_document" as const,
      }),
    ),
    linkToCustomer: vi.fn(() => Promise.resolve()),
    linkToReceivable: vi.fn(() => Promise.reject(new Error("non utilisé"))),
    ...overrides,
  };
}

function renderWith(gateway: AttachmentsGateway, ui: React.ReactElement, applyAccept = true) {
  const user = userEvent.setup({ applyAccept });
  const view = render(
    <AttachmentsContext.Provider value={gateway}>{ui}</AttachmentsContext.Provider>,
  );
  return { user, ...view };
}

const LABEL = "Photo de la pièce d'identité";

describe("envoi d'une pièce jointe", () => {
  it("stockage indisponible : message, photo gardée, « Réessayer » renvoie le même identifiant", async () => {
    const upload = vi
      .fn<AttachmentsGateway["upload"]>()
      .mockRejectedValueOnce(new ApiError(503, "STORAGE_UNAVAILABLE", "Stockage indisponible"))
      .mockResolvedValueOnce(attachment());
    const onUploaded = vi.fn();
    const { user, container } = renderWith(
      fakeGateway({ upload }),
      <AttachmentUpload
        shopId={SHOP_A}
        ownerType="customer"
        ownerId="cust-1"
        kind="id_document"
        label={LABEL}
        onUploaded={onUploaded}
        codec={fakeCodec()}
      />,
    );
    await user.upload(screen.getByLabelText(LABEL), photoFile());
    expect(await screen.findByText(STORAGE_DOWN)).toBeVisible();
    expect(onUploaded).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Réessayer l'envoi" }));
    expect(await screen.findByText("Pièce enregistrée.")).toBeVisible();
    expect(onUploaded).toHaveBeenCalledWith(attachment());
    const [first, second] = upload.mock.calls.map((call) => call[1]);
    expect(second?.id).toBe(first?.id);
    expect([first?.ownerType, first?.ownerId, first?.fileName]).toEqual([
      "customer",
      "cust-1",
      "IMG_0001.jpg",
    ]);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("fichier refusé ou coupure réseau : message clair, rien n'est rattaché", async () => {
    const upload = vi.fn(() => Promise.reject(new NetworkError("coupure")));
    const onUploaded = vi.fn();
    const { user } = renderWith(
      fakeGateway({ upload }),
      <AttachmentUpload
        shopId={SHOP_A}
        ownerType="receivable"
        ownerId="sale-124"
        kind="contract"
        label="Ajouter : Contrat"
        onUploaded={onUploaded}
        codec={fakeCodec()}
      />,
      false, // le téléphone peut proposer un fichier hors de `accept`
    );
    const picker = screen.getByLabelText("Ajouter : Contrat");
    await user.upload(picker, new File(["x"], "note.txt", { type: "text/plain" }));
    expect(await screen.findByText(/Format refusé/)).toBeVisible();
    expect(upload).not.toHaveBeenCalled();
    await user.upload(picker, photoFile());
    expect(await screen.findByText(/Connexion nécessaire/)).toBeVisible();
    expect(onUploaded).not.toHaveBeenCalled();
  });
});

describe("affichage d'une pièce jointe", () => {
  it("photo : lien demandé à l'appui puis image affichée ; PDF : ouvert à part", async () => {
    const link = vi.fn<AttachmentsGateway["link"]>(() =>
      Promise.resolve({
        url: CONTENT_URL,
        expiresAt: new Date(),
        mime: "image/jpeg",
        kind: "id_document",
      }),
    );
    const gateway = fakeGateway({ link });
    const { user } = renderWith(
      gateway,
      <AttachmentView shopId={SHOP_A} attachmentId="a-1" label="pièce d'identité de Ali" />,
    );
    expect(link).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Voir : pièce d'identité de Ali" }));
    expect(await screen.findByRole("img", { name: "pièce d'identité de Ali" })).toHaveAttribute(
      "src",
      CONTENT_URL,
    );

    const open = vi.fn();
    const pdf = fakeGateway({
      link: () =>
        Promise.resolve({
          url: "/pdf",
          expiresAt: new Date(),
          mime: "application/pdf",
          kind: "contract",
        }),
    });
    renderWith(
      pdf,
      <AttachmentView shopId={SHOP_A} attachmentId="a-2" label="contrat" openWindow={open} />,
    );
    await user.click(screen.getByRole("button", { name: "Voir : contrat" }));
    expect(open).toHaveBeenCalledWith("/pdf");
  });

  it("pièce réservée : message, aucune image", async () => {
    const link = () => Promise.reject(new ApiError(404, "NOT_FOUND", "Élément introuvable"));
    const { user } = renderWith(
      fakeGateway({ link }),
      <AttachmentView shopId={SHOP_A} attachmentId="a-1" label="pièce" />,
    );
    await user.click(screen.getByRole("button", { name: "Voir : pièce" }));
    expect(
      await screen.findByText(/réservée au propriétaire et au vendeur responsable/),
    ).toBeVisible();
    expect(screen.queryByRole("img")).toBeNull();
  });
});
