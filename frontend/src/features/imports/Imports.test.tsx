import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Role } from "../../core/auth/me";
import { ApiError, NetworkError } from "../../core/api/errors";
import { ImportsContext } from "../../core/gateways/httpImports";
import { MODULE_DISABLED_MESSAGE, type ModuleCode } from "../../core/profile/modules";
import { axeViolations } from "../../testing/axe";
import { SHOP_A } from "../../testing/fakeApi";
import { fakeImportsGateway, type ImportsMocks } from "../../testing/importsGateway";
import { forcedModules, importPreview, PREVIEW_ID } from "../../testing/imports";
import type { ImportsGateway } from "../../core/gateways/importsContract";
import { DOWNLOAD_LABEL, DROP_LABEL } from "./FileStep";
import { EXPIRED, importFailure, NOTHING_VALID } from "./importErrors";
import { modelsFor } from "./importModels";
import { ImportsPage } from "./ImportsPage";
import type { SaveFile } from "./saveFile";
import { CONFIRM_LABEL } from "./PreviewStep";

const fakeGateway = fakeImportsGateway;

interface Setup {
  gateway?: ImportsMocks;
  role?: Role;
  off?: ModuleCode[];
}

function renderPage({ gateway = fakeGateway(), role = "owner", off = [] }: Setup = {}) {
  const user = userEvent.setup();
  const save = vi.fn<SaveFile>();
  const models = modelsFor(role, forcedModules(off));
  const view = render(
    <ImportsContext.Provider value={gateway}>
      <ImportsPage shopId={SHOP_A} models={models} save={save} />
    </ImportsContext.Provider>,
  );
  return { user, save, gateway, ...view };
}

const csv = () => new File(["nom;prix"], "articles.csv", { type: "text/csv" });
const modelNames = () =>
  within(screen.getByRole("list", { name: "Modèles d'import" }))
    .getAllByRole("button")
    .map((button) => button.textContent);

async function upToPreview(setup: Setup = {}) {
  const page = renderPage(setup);
  await page.user.click(screen.getByRole("button", { name: /^Articles/ }));
  await page.user.upload(screen.getByLabelText(DROP_LABEL), csv());
  await screen.findByRole("heading", { name: "Erreurs" });
  return page;
}

describe("Import : choix du modèle (UC-IMP-01)", () => {
  it("propriétaire, tous modules actifs : les 5 modèles", () => {
    renderPage();
    expect(modelNames()).toHaveLength(5);
    expect(screen.getByText("Étape 1 sur 4")).toBeVisible();
  });

  it.each<[Role, ModuleCode[], string[]]>([
    ["accountant", [], ["Articles", "Stock de départ", "Fournisseurs"]],
    ["owner", ["receivables", "purchases"], ["Articles", "Stock de départ", "Clients"]],
  ])("rôle %s, modules éteints %j", (role, off, expected) => {
    renderPage({ role, off });
    expect(modelNames()).toHaveLength(expected.length);
    for (const label of expected) {
      expect(screen.getByRole("button", { name: new RegExp(`^${label}`) })).toBeVisible();
    }
  });

  it("télécharge le modèle choisi puis l'enregistre", async () => {
    const { user, save, gateway } = renderPage();
    await user.click(screen.getByRole("button", { name: /^Stock de départ/ }));
    expect(screen.getByRole("heading", { name: "Import : Stock de départ" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: DOWNLOAD_LABEL }));
    expect(gateway.template).toHaveBeenCalledWith(SHOP_A, "opening_stock");
    const [saved] = save.mock.calls[0] ?? [];
    expect(saved).toMatchObject({ fileName: "modele.xlsx" });
  });
});

describe("Import : dépôt et aperçu (UC-IMP-02, IMP-12)", () => {
  it("aperçu : lignes prêtes, écartées, éléments créés, erreurs « Ligne N : … » ; axe", async () => {
    const { gateway, container } = await upToPreview();
    expect(gateway.preview).toHaveBeenCalledWith(SHOP_A, "articles", expect.any(File));
    expect(screen.getByText("Étape 3 sur 4")).toBeVisible();
    const summary = screen.getByRole("list", { name: "Bilan de l'aperçu" });
    expect(within(summary).getByText("2 lignes prêtes")).toBeVisible();
    expect(within(summary).getByText("2 lignes écartées")).toBeVisible();
    expect(within(summary).getByText("2 articles nouveaux seront créés")).toBeVisible();
    const errors = screen.getByRole("list", { name: "Erreurs du fichier" });
    expect(within(errors).getByText("Ligne 5 : le nom est vide")).toBeVisible();
    expect(screen.getByRole("button", { name: CONFIRM_LABEL })).toBeEnabled();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("« Importer les lignes valides » : rapport avec le numéro IMP-… ; axe", async () => {
    const { user, gateway, container } = await upToPreview();
    await user.click(screen.getByRole("button", { name: CONFIRM_LABEL }));
    expect(await screen.findByText("Import IMP-000001 enregistré")).toBeVisible();
    expect(gateway.confirm).toHaveBeenCalledWith(SHOP_A, PREVIEW_ID);
    const report = screen.getByRole("list", { name: "Rapport de l'import" });
    expect(within(report).getByText("2 lignes importées")).toBeVisible();
    expect(within(report).getByText("2 articles créés")).toBeVisible();
    expect(screen.getByText("Étape 4 sur 4")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("aucune ligne valide : bouton indisponible avec la raison", async () => {
    const preview = vi.fn(() => Promise.resolve(importPreview({ rows_valid: 0, notes: [] })));
    const { user, gateway } = await upToPreview({ gateway: fakeGateway({ preview }) });
    const button = screen.getByRole("button", { name: CONFIRM_LABEL });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveAccessibleDescription(NOTHING_VALID);
    await user.click(button);
    expect(gateway.confirm).not.toHaveBeenCalled();
  });

  it("410 : « L'aperçu a expiré » et retour au dépôt du fichier", async () => {
    const confirm = vi.fn(() =>
      Promise.reject(new ApiError(410, "IMPORT_PREVIEW_EXPIRED", "Aperçu expiré")),
    );
    const { user } = await upToPreview({ gateway: fakeGateway({ confirm }) });
    await user.click(screen.getByRole("button", { name: CONFIRM_LABEL }));
    expect(await screen.findByText(EXPIRED)).toBeVisible();
    expect(screen.getByText("Étape 2 sur 4")).toBeVisible();
    expect(screen.getByLabelText(DROP_LABEL)).toBeInTheDocument();
  });

  it("422 à la confirmation : retour au dépôt avec « Aucune ligne à importer »", async () => {
    const confirm = vi.fn(() =>
      Promise.reject(new ApiError(422, "VALIDATION_ERROR", "Aucune ligne valide")),
    );
    const { user } = await upToPreview({ gateway: fakeGateway({ confirm }) });
    await user.click(screen.getByRole("button", { name: CONFIRM_LABEL }));
    expect(await screen.findByText(NOTHING_VALID)).toBeVisible();
    expect(screen.getByText("Étape 2 sur 4")).toBeVisible();
  });

  it("fichier refusé (400) ou module éteint (403) : message lisible, on reste au dépôt", async () => {
    const preview = vi
      .fn<ImportsGateway["preview"]>()
      .mockRejectedValueOnce(
        new ApiError(400, "IMPORT_FILE_INVALID", "Fichier refusé", {
          reason: "format .xls (Excel 97-2003) non pris en charge : enregistrer en .xlsx",
        }),
      )
      .mockRejectedValueOnce(new ApiError(403, "MODULE_DISABLED", "Module éteint"))
      .mockRejectedValueOnce(new NetworkError("coupure"));
    const { user } = renderPage({ gateway: fakeGateway({ preview }) });
    await user.click(screen.getByRole("button", { name: /^Articles/ }));
    await user.upload(screen.getByLabelText(DROP_LABEL), csv());
    expect(await screen.findByText(/Ce fichier ne se lit pas : format \.xls/)).toBeVisible();
    await user.upload(screen.getByLabelText(DROP_LABEL), csv());
    expect(await screen.findByText(MODULE_DISABLED_MESSAGE)).toBeVisible();
    await user.upload(screen.getByLabelText(DROP_LABEL), csv());
    expect(await screen.findByText(/Connexion nécessaire/)).toBeVisible();
    expect(screen.getByText("Étape 2 sur 4")).toBeVisible();
  });

  it("erreur imprévue : relancée (fail-fast), jamais avalée en message", () => {
    const bug = new TypeError("bug");
    expect(() => importFailure(bug)).toThrow(bug);
    const other = importFailure(new ApiError(409, "CONFLICT", "Déjà en cours"));
    expect(other).toEqual({
      text: "L'import n'a pas abouti : Déjà en cours (CONFLICT).",
      restart: false,
    });
  });
});
