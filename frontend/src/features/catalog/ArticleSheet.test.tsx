import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  accountantArticle,
  API,
  catalogRoutes,
  HAOJUE_ID,
  ownerArticle,
} from "../../testing/catalog";
import { apiError, json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { money } from "../../testing/renderSale";
import { VERSION_CONFLICT_MESSAGE } from "./catalogErrors";

const SHEET = `/s/${SHOP_A}/stock?article=${HAOJUE_ID}`;
const GET = `GET ${API}/articles/${HAOJUE_ID}`;
const PATCH = `PATCH ${API}/articles/${HAOJUE_ID}`;

// Premier rendu : écran chargé à la demande + restauration de session ; sous la charge de la
// suite complète, il dépasse parfois le délai d'attente par défaut (1 s) de Testing Library.
configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

const section = (name: string) => screen.findByRole("region", { name });

describe("fiche article — propriétaire", () => {
  it("détails du profil, prix, coûts « non calculable », historique des prix", async () => {
    const article = ownerArticle({
      price_history: [
        {
          price_kind: "base_price",
          old_price: 750000,
          new_price: 780000,
          effective_at: "2026-11-05T09:30:00Z",
          author_id: "u1",
        },
      ],
    });
    const { container } = renderApp(SHEET, catalogRoutes("owner", { [GET]: json(200, article) }));
    expect(await screen.findByRole("heading", { name: "Haojue HJ125-8" })).toBeVisible();
    const details = await section("Détails");
    expect(details).toHaveTextContent("MarqueHaojue");
    expect(details).toHaveTextContent("Cylindrée (cm³)125");
    expect(details).toHaveTextContent("Catégorie—");
    expect(details).toHaveTextContent("Seuil d'alerte2 (réglage de la boutique)");
    const prices = await section("Prix de vente");
    expect(prices).toHaveTextContent(`Prix de base${money(780000)}`);
    expect(prices).toHaveTextContent(`Prix minimum${money(720000)}`);
    const costs = await section("Coûts");
    expect(costs).toHaveTextContent(`Dernier coût d'achat${money(650000)}`);
    expect(costs).toHaveTextContent("Coût moyen (CMP)non calculable");
    const history = await section("Historique des prix");
    expect(history).toHaveTextContent(`${money(750000)} → ${money(780000)}`);
    expect(history).toHaveTextContent("05/11/2026");
    for (const name of ["Modifier l'article", "Modifier les prix", "Archiver l'article"]) {
      expect(screen.getByRole("button", { name })).toBeVisible();
    }
    expect(await axeViolations(container)).toEqual([]);
  });

  it("modification : n'envoie que les champs changés, la version et le motif", async () => {
    const saved = ownerArticle({ version: 4, attributes: { engine_cc: 150 } });
    const { user, fake } = renderApp(
      SHEET,
      catalogRoutes("owner", { [GET]: json(200, ownerArticle()), [PATCH]: json(200, saved) }),
    );
    await user.click(await screen.findByRole("button", { name: "Modifier l'article" }));
    const engine = screen.getByLabelText("Cylindrée (cm³)");
    await user.clear(engine);
    await user.type(engine, "150");
    await user.type(screen.getByLabelText("Motif (facultatif)"), "Fiche fournisseur");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Article enregistré")).toBeVisible();
    const call = fake.calls.find((c) => c.method === "PATCH");
    expect(call?.body).toEqual({
      version: 3,
      fields: { engine_cc: 150 },
      reason: "Fiche fournisseur",
    });
    expect(await section("Détails")).toHaveTextContent("Cylindrée (cm³)150");
  });

  it("modification : un champ obligatoire vidé est refusé avant l'envoi ; rien changé = rien envoyé", async () => {
    const { user, fake } = renderApp(
      SHEET,
      catalogRoutes("owner", { [GET]: json(200, ownerArticle()) }),
    );
    await user.click(await screen.findByRole("button", { name: "Modifier l'article" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(screen.getByText("Aucun changement à enregistrer.")).toBeVisible();
    await user.clear(screen.getByLabelText("Marque"));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(screen.getByText("Marque : champ obligatoire")).toBeVisible();
    expect(fake.count(PATCH)).toBe(0);
    await user.click(screen.getByRole("button", { name: "Annuler la modification" }));
    expect(await section("Détails")).toBeVisible();
  });

  it("conflit de version : message clair, puis « Recharger l'article » relit la fiche", async () => {
    const { user, fake } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [GET]: [json(200, ownerArticle()), json(200, ownerArticle({ version: 5, model: "HJ150" }))],
        [PATCH]: apiError(409, "VERSION_CONFLICT", "Version périmée"),
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Modifier l'article" }));
    await user.type(screen.getByLabelText("Catégorie"), "Moto de route");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText(VERSION_CONFLICT_MESSAGE)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Recharger l'article" }));
    expect(await section("Détails")).toHaveTextContent("ModèleHJ150");
    expect(fake.count(GET)).toBe(2);
  });

  it("modification qui crée un doublon : propose l'article existant", async () => {
    const { user, router } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [GET]: json(200, ownerArticle()),
        [PATCH]: apiError(409, "DUPLICATE", "Cet article existe déjà", {
          existing_id: "other-id",
          existing_name: "Haojue HJ125-7",
          constraint: "brand_model",
        }),
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Modifier l'article" }));
    const model = screen.getByLabelText("Modèle");
    await user.clear(model);
    await user.type(model, "HJ125-7");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Cet article existe déjà : Haojue HJ125-7")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Ouvrir « Haojue HJ125-7 »" }));
    expect(router.state.location.search).toBe("?article=other-id");
  });
});

describe("fiche article — comptable et refus", () => {
  it("comptable : coûts sans prix de vente, ni prix ni archivage proposés", async () => {
    const { container } = renderApp(
      SHEET,
      catalogRoutes("accountant", { [GET]: json(200, accountantArticle()) }),
    );
    expect(await section("Coûts")).toHaveTextContent(`Dernier coût d'achat${money(650000)}`);
    expect(screen.queryByRole("region", { name: "Prix de vente" })).toBeNull();
    expect(screen.queryByText(/Prix de base|Prix minimum/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Modifier les prix" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Archiver/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Modifier l'article" })).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("article introuvable : message, retour à la liste", async () => {
    const { user, router } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [GET]: apiError(404, "NOT_FOUND", "Article introuvable"),
        [`GET ${API}/articles?status=active&limit=20`]: json(200, { items: [], next_cursor: null }),
      }),
    );
    expect(await screen.findByText("Cet article est introuvable.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retour aux articles" }));
    expect(router.state.location.search).toBe("");
    expect(within(document.body).getByRole("heading", { name: "Articles" })).toBeVisible();
  });
});
