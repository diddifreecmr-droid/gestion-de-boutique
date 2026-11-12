import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { AttachmentsGateway } from "../../core/gateways/attachmentsContract";
import { AttachmentsContext } from "../../core/gateways/httpAttachments";
import {
  attachment,
  ATTACHMENT_ID,
  CONTENT_URL,
  LINK,
  linkBody,
  pdfFile,
  UPLOAD,
} from "../../testing/attachments";
import { axeViolations } from "../../testing/axe";
import { setClock } from "../../testing/expensesApi";
import { json, SHOP_A } from "../../testing/fakeApi";
import {
  DETAIL_PATH,
  GET_ONE,
  NOW,
  preloadReceivables,
  receivable,
  receivableRoutes,
  RECEIVABLE_ID,
  route,
} from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";
import { CreditIdPhoto } from "../sales/CreditIdPhoto";

beforeAll(preloadReceivables);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});

describe("Pièces jointes de la créance (UC-CRE-07)", () => {
  it("contrat ajouté : envoi, rattachement (version relue), puis « Voir » affiche la pièce", async () => {
    const before = receivable({ version: 3, attachment_ids: [] });
    const after = receivable({ version: 4, attachment_ids: [ATTACHMENT_ID] });
    const { user, fake, container } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("seller"),
      [GET_ONE]: [json(200, before), json(200, before)],
      [route("PATCH", `/receivables/${RECEIVABLE_ID}`)]: json(200, after),
      [UPLOAD]: json(201, attachment({ kind: "contract", mime: "application/pdf" })),
      [LINK]: json(200, linkBody()),
    });
    await screen.findByRole("heading", { name: "Créance de Moussa Hamadou" });
    const section = within(screen.getByRole("region", { name: "Pièces jointes" }));
    expect(section.getByText("Aucune pièce jointe.")).toBeVisible();
    await user.click(section.getByRole("radio", { name: "Contrat" }));
    await user.upload(section.getByLabelText("Ajouter : Contrat"), pdfFile());
    const view = await section.findByRole("button", { name: "Voir : pièce jointe n° 1" });
    const form = fake.calls.find((c) => `${c.method} ${c.url}` === UPLOAD)?.form;
    expect([form?.get("owner_type"), form?.get("kind")]).toEqual(["receivable", "contract"]);
    const patch = fake.calls.find((c) => c.method === "PATCH");
    expect(patch?.body).toEqual({ version: 3, attachment_ids: [ATTACHMENT_ID] });
    await user.click(view);
    expect(await section.findByRole("img", { name: "pièce jointe n° 1" })).toHaveAttribute(
      "src",
      CONTENT_URL,
    );
    expect(await axeViolations(container)).toEqual([]);
  });
});

describe("Vente à crédit : pièce d'identité du client (UC-VEN-02)", () => {
  it("la photo envoyée est rattachée à la fiche du client", async () => {
    const linkToCustomer = vi.fn(() => Promise.resolve());
    const gateway: AttachmentsGateway = {
      upload: vi.fn(() => Promise.resolve(attachment({ owner_type: "customer" }))),
      link: vi.fn(),
      linkToCustomer,
      linkToReceivable: vi.fn(),
    };
    const user = userEvent.setup();
    render(
      <AttachmentsContext.Provider value={gateway}>
        <CreditIdPhoto shopId={SHOP_A} customerId="cust-moussa" />
      </AttachmentsContext.Provider>,
    );
    expect(screen.getByRole("heading", { name: "Pièce d'identité du client" })).toBeVisible();
    await user.upload(screen.getByLabelText("Photo de la pièce d'identité"), pdfFile());
    expect(await screen.findByText("Pièce enregistrée.")).toBeVisible();
    expect(linkToCustomer).toHaveBeenCalledWith(SHOP_A, "cust-moussa", ATTACHMENT_ID);
  });
});
