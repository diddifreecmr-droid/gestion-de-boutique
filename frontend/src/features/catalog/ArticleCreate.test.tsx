import { configure, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import {
  accountantArticle,
  API,
  catalogRoutes,
  HAOJUE_ID,
  listUrl,
  ownerArticle,
} from "../../testing/catalog";
import { apiError, json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { replaceText } from "../../testing/renderSale";
import { OFFLINE_SAVE } from "./catalogErrors";

const NEW = `/s/${SHOP_A}/stock?article=nouveau`;
const POST = `POST ${API}/articles`;
const GET = `GET ${API}/articles/${HAOJUE_ID}`;

// Premier rendu : écran chargé à la demande + restauration de session ; sous la charge de la
// suite complète, il dépasse parfois le délai d'attente par défaut (1 s) de Testing Library.
configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

function input(label: string): HTMLInputElement {
  const field = screen.getByLabelText(label);
  if (!(field instanceof HTMLInputElement)) throw new Error(`« ${label} » n'est pas un champ`);
  return field;
}

describe("« Nouvel article »", () => {
  it("depuis la liste : marque et modèle visibles, facultatifs sous « Plus de détails »", async () => {
    const { user, container } = renderApp(
      `/s/${SHOP_A}/stock`,
      catalogRoutes("owner", { [listUrl()]: json(200, { items: [], next_cursor: null }) }),
    );
    await user.click(await screen.findByRole("button", { name: "Nouvel article" }));
    expect(await screen.findByRole("heading", { name: "Nouvel article" })).toBeVisible();
    expect(input("Marque")).toBeVisible();
    expect(input("Modèle")).toBeVisible();
    expect(input("Prix de base (facultatif)")).toBeVisible();
    expect(input("Cylindrée (cm³)")).not.toBeVisible();
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    expect(input("Cylindrée (cm³)")).toBeVisible();
    expect(input("Seuil d'alerte")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("propriétaire : crée avec un id UUIDv7, les champs du profil et le prix de base", async () => {
    const { user, fake, router } = renderApp(
      NEW,
      catalogRoutes("owner", {
        [POST]: json(201, ownerArticle()),
        [GET]: json(200, ownerArticle()),
      }),
    );
    await user.type(await screen.findByLabelText("Marque"), "Haojue");
    await user.type(input("Modèle"), "HJ125-8");
    await replaceText(user, input("Prix de base (facultatif)"), "780000");
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.type(input("Cylindrée (cm³)"), "125");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(await screen.findByText("Article créé : Haojue HJ125-8")).toBeVisible();
    expect(router.state.location.search).toBe(`?article=${HAOJUE_ID}`);
    const body = fake.calls.find((c) => c.method === "POST" && c.url.endsWith("/articles"))
      ?.body as Record<string, unknown>;
    expect(isUuidV7(String(body["id"]))).toBe(true);
    expect(body).toMatchObject({
      fields: { brand: "Haojue", model: "HJ125-8", engine_cc: 125 },
      base_price: 780000,
      min_price: null,
      alert_threshold: null,
      notes: null,
    });
  });

  it("champs obligatoires et cylindrée invalide : refusés avant l'envoi", async () => {
    const { user, fake } = renderApp(NEW, catalogRoutes("owner"));
    await user.click(await screen.findByRole("button", { name: "Créer l'article" }));
    expect(screen.getByText("Marque : champ obligatoire")).toBeVisible();
    expect(screen.getByText("Modèle : champ obligatoire")).toBeVisible();
    await user.type(input("Marque"), "Haojue");
    await user.type(input("Modèle"), "HJ");
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.type(input("Cylindrée (cm³)"), "12,5");
    await user.type(input("Seuil d'alerte"), "abc");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(screen.getByText("Cylindrée (cm³) : nombre entier attendu (ex. 125)")).toBeVisible();
    expect(screen.getByText("Seuil d'alerte : nombre attendu (ex. 5)")).toBeVisible();
    expect(fake.count(POST)).toBe(0);
  });

  it("doublon : « Cet article existe déjà : Haojue HJ125-8 » et lien vers l'existant", async () => {
    const { user, router } = renderApp(
      NEW,
      catalogRoutes("owner", {
        [POST]: apiError(409, "DUPLICATE", "Cet article existe déjà", {
          existing_id: HAOJUE_ID,
          existing_name: "Haojue HJ125-8",
          constraint: "brand_model",
        }),
        [GET]: json(200, ownerArticle()),
      }),
    );
    await user.type(await screen.findByLabelText("Marque"), "haojue");
    await user.type(input("Modèle"), "hj125-8");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(await screen.findByText("Cet article existe déjà : Haojue HJ125-8")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Ouvrir « Haojue HJ125-8 »" }));
    expect(router.state.location.search).toBe(`?article=${HAOJUE_ID}`);
    expect(await screen.findByRole("heading", { name: "Haojue HJ125-8" })).toBeVisible();
  });

  it("comptable : aucun champ de prix, aucun prix envoyé", async () => {
    const { user, fake } = renderApp(
      NEW,
      catalogRoutes("accountant", {
        [POST]: json(201, accountantArticle()),
        [GET]: json(200, accountantArticle()),
      }),
    );
    await user.type(await screen.findByLabelText("Marque"), "Haojue");
    expect(screen.queryByLabelText(/Prix/)).toBeNull();
    await user.type(input("Modèle"), "HJ125-8");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(await screen.findByText("Article créé : Haojue HJ125-8")).toBeVisible();
    const body = fake.calls.find((c) => c.url.endsWith("/articles"))?.body as object;
    expect(Object.keys(body).some((key) => key.includes("price"))).toBe(false);
  });

  it("coupure à l'envoi : message, la saisie reste, le même id repart", async () => {
    const { user, fake } = renderApp(
      NEW,
      catalogRoutes("owner", {
        [POST]: [new TypeError("Failed to fetch"), json(201, ownerArticle())],
        [GET]: json(200, ownerArticle()),
      }),
    );
    await user.type(await screen.findByLabelText("Marque"), "Haojue");
    await user.type(input("Modèle"), "HJ125-8");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(await screen.findByText(OFFLINE_SAVE)).toBeVisible();
    expect(input("Marque").value).toBe("Haojue");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(await screen.findByText("Article créé : Haojue HJ125-8")).toBeVisible();
    const ids = fake.calls
      .filter((c) => c.method === "POST" && c.url.endsWith("/articles"))
      .map((c) => (c.body as Record<string, unknown>)["id"]);
    expect(ids).toHaveLength(2);
    expect(ids[0]).toBe(ids[1]);
  });
});
