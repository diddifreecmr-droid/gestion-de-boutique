import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Role } from "../../core/auth/me";
import { ApiError } from "../../core/api/errors";
import { axeViolations } from "../../testing/axe";
import { SHOP_A } from "../../testing/fakeApi";
import { forcedModules, importBatch, importBatchDetail } from "../../testing/imports";
import { fakeImportsGateway, type ImportsMocks } from "../../testing/importsGateway";
import { ImportsContext } from "../../core/gateways/httpImports";
import { HISTORY_LABEL, NO_BATCH } from "./BatchList";
import { ERRORS_LABEL } from "./BatchDetail";
import { CANCEL_EFFECT, CANCEL_LABEL, CANCELLED } from "./CancelImport";
import { ALREADY_CANCELLED, BLOCKED } from "./cancelErrors";
import { modelsFor } from "./importModels";
import { ImportsScreen } from "./ImportsScreen";
import type { SaveFile } from "./saveFile";

const TODAY = "2026-11-13";

interface Setup {
  gateway?: ImportsMocks;
  role?: Role;
  today?: string;
}

async function openHistory({
  gateway = fakeImportsGateway(),
  role = "owner",
  today = TODAY,
}: Setup = {}) {
  const user = userEvent.setup();
  const save = vi.fn<SaveFile>();
  const view = render(
    <ImportsContext.Provider value={gateway}>
      <ImportsScreen
        shopId={SHOP_A}
        role={role}
        models={modelsFor(role, forcedModules())}
        save={save}
        today={today}
      />
    </ImportsContext.Provider>,
  );
  await user.click(screen.getByRole("button", { name: HISTORY_LABEL }));
  return { user, save, gateway, ...view };
}

async function openDetail(setup: Setup = {}) {
  const page = await openHistory(setup);
  await page.user.click(await screen.findByRole("button", { name: /^IMP-000001/ }));
  await screen.findByRole("list", { name: "Bilan du lot" });
  return page;
}

async function askCancel(page: Awaited<ReturnType<typeof openDetail>>) {
  await page.user.click(screen.getByRole("button", { name: CANCEL_LABEL }));
  const dialog = screen.getByRole("dialog");
  expect(dialog).toHaveTextContent(CANCEL_EFFECT);
  await page.user.click(within(dialog).getByRole("button", { name: CANCEL_LABEL }));
}

describe("Imports passés : liste des lots (T45)", () => {
  it("numéro, modèle, date, lignes, pastille, « Annulable jusqu'au JJ/MM » ; axe", async () => {
    const list = vi.fn(() =>
      Promise.resolve([
        importBatch(),
        importBatch({
          id: "batch-2",
          number: "IMP-000002",
          kind: "customers",
          status: "cancelled",
          rows_ignored: 0,
          cancelled_at: "2026-11-13T11:00:00Z",
        }),
      ]),
    );
    const { container } = await openHistory({ gateway: fakeImportsGateway({ list }) });
    const rows = within(await screen.findByRole("list", { name: HISTORY_LABEL })).getAllByRole(
      "listitem",
    );
    expect(rows[0]).toHaveTextContent("IMP-000001 · Articles");
    expect(rows[0]).toHaveTextContent(
      "13/11/2026 · 2 lignes importées, 2 ignorées · Annulable jusqu'au 20/11",
    );
    expect(rows[0]).toHaveTextContent("Importé");
    expect(rows[1]).toHaveTextContent("IMP-000002 · Clients");
    expect(rows[1]).toHaveTextContent("Annulé");
    expect(rows[1]).not.toHaveTextContent("Annulable");
    expect(list).toHaveBeenCalledWith(SHOP_A);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("aucun lot : message vide", async () => {
    await openHistory({ gateway: fakeImportsGateway({ list: vi.fn(() => Promise.resolve([])) }) });
    expect(await screen.findByText(NO_BATCH)).toBeVisible();
  });
});

describe("Imports passés : détail d'un lot", () => {
  it("auteur, éléments créés, problèmes ; « Télécharger les erreurs » enregistre errors.xlsx ; axe", async () => {
    const { user, save, gateway, container } = await openDetail();
    expect(screen.getByRole("heading", { name: "Import IMP-000001" })).toBeVisible();
    expect(screen.getByText(/par Awa Propriétaire/)).toBeVisible();
    const report = screen.getByRole("list", { name: "Bilan du lot" });
    expect(report).toHaveTextContent("2 articles créés");
    expect(report).toHaveTextContent("2 problèmes relevés");
    await user.click(screen.getByRole("button", { name: ERRORS_LABEL }));
    expect(gateway.errors).toHaveBeenCalledWith(SHOP_A, "batch-1");
    expect(save).toHaveBeenCalledWith(
      expect.objectContaining({ fileName: "erreurs-IMP-000001.xlsx" }),
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("aucun problème : pas de rapport d'erreurs ; comptable : pas d'annulation", async () => {
    const detail = vi.fn(() => Promise.resolve(importBatchDetail({ problems_total: 0 })));
    await openDetail({ gateway: fakeImportsGateway({ detail }), role: "accountant" });
    expect(screen.queryByRole("button", { name: ERRORS_LABEL })).toBeNull();
    expect(screen.queryByRole("button", { name: CANCEL_LABEL })).toBeNull();
  });

  it("délai passé : pas de bouton, « annulation possible jusqu'au 20/11 »", async () => {
    await openDetail({ today: "2026-11-21" });
    expect(screen.queryByRole("button", { name: CANCEL_LABEL })).toBeNull();
    expect(screen.getByText(/annulation possible jusqu'au 20\/11/)).toBeVisible();
  });
});

describe("Annuler l'import (propriétaire, UC-IMP-03)", () => {
  it("confirmation qui dit l'effet, annulation, lot relu : « Annulé »", async () => {
    const detail = vi
      .fn(() => Promise.resolve(importBatchDetail()))
      .mockResolvedValueOnce(importBatchDetail())
      .mockResolvedValueOnce(
        importBatchDetail({ status: "cancelled", cancelled_at: "2026-11-14T08:00:00Z" }),
      );
    const page = await openDetail({ gateway: fakeImportsGateway({ detail }) });
    await askCancel(page);
    expect(page.gateway.cancel).toHaveBeenCalledWith(SHOP_A, "batch-1");
    expect(await screen.findByText(CANCELLED)).toBeVisible();
    expect(await screen.findByText(/Annulé le 14\/11\/2026/)).toBeVisible();
    expect(screen.queryByRole("button", { name: CANCEL_LABEL })).toBeNull();
  });

  it("refus IMPORT_CANCEL_BLOCKED : les opérations qui bloquent, en français", async () => {
    const blocking = [
      { type: "sale", number: "V-000003" },
      { type: "payment", number: "VR-000001" },
    ];
    const cancel = vi.fn(() =>
      Promise.reject(new ApiError(422, "IMPORT_CANCEL_BLOCKED", "Bloqué", { blocking })),
    );
    const page = await openDetail({ gateway: fakeImportsGateway({ cancel }) });
    await askCancel(page);
    expect(await screen.findByText(BLOCKED)).toBeVisible();
    const items = screen.getByRole("list", { name: "Opérations qui bloquent" });
    expect(
      within(items)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["la vente V-000003", "le versement VR-000001"]);
  });

  it.each([
    ["IMPORT_CANCEL_TOO_LATE", "Délai dépassé : annulation possible jusqu'au 20/11."],
    ["INVALID_STATE_TRANSITION", ALREADY_CANCELLED],
  ])("refus %s : message et lot relu", async (code, text) => {
    const cancel = vi.fn(() => Promise.reject(new ApiError(422, code, "Refusé", {})));
    const page = await openDetail({ gateway: fakeImportsGateway({ cancel }) });
    await askCancel(page);
    expect(await screen.findByText(text)).toBeVisible();
    expect(page.gateway.detail).toHaveBeenCalledTimes(2);
  });
});
