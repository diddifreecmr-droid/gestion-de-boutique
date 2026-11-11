import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { API, catalogRoutes, HAOJUE_ID, ownerArticle, profileBody } from "../../testing/catalog";
import { apiError, json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { money, replaceText } from "../../testing/renderSale";
import { HAS_STOCK_MESSAGE, MIN_DISABLED_MESSAGE } from "./catalogErrors";

const SHEET = `/s/${SHOP_A}/stock?article=${HAOJUE_ID}`;
const GET = `GET ${API}/articles/${HAOJUE_ID}`;
const PUT = `PUT ${API}/articles/${HAOJUE_ID}/prices`;
const ARCHIVE = `POST ${API}/articles/${HAOJUE_ID}/archive`;
const REACTIVATE = `POST ${API}/articles/${HAOJUE_ID}/reactivate`;

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

async function openPrices(user: ReturnType<typeof renderApp>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Modifier les prix" }));
}

describe("prix (propriétaire)", () => {
  it("PUT des quatre prix avec la version ; la fiche montre les nouveaux prix", async () => {
    const saved = ownerArticle({ version: 4, base_price: 800000, min_price: 750000 });
    const { user, fake } = renderApp(
      SHEET,
      catalogRoutes("owner", { [GET]: json(200, ownerArticle()), [PUT]: json(200, saved) }),
    );
    await openPrices(user);
    await replaceText(user, input("Prix de base"), "800000");
    await replaceText(user, input("Prix minimum"), "750000");
    await user.click(screen.getByRole("button", { name: "Enregistrer les prix" }));
    expect(await screen.findByText("Prix enregistrés")).toBeVisible();
    expect(fake.calls.find((c) => c.method === "PUT")?.body).toEqual({
      version: 3,
      base_price: 800000,
      min_price: 750000,
      base_price_piece: null,
      min_price_piece: null,
    });
    const prices = await screen.findByRole("region", { name: "Prix de vente" });
    expect(prices).toHaveTextContent(`Prix de base${money(800000)}`);
  });

  it("MIN_PRICE_ABOVE_BASE : les deux montants dans le message", async () => {
    const { user } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [GET]: json(200, ownerArticle()),
        [PUT]: apiError(422, "MIN_PRICE_ABOVE_BASE", "Le prix minimum ne peut pas dépasser", {
          field: "min_price",
          min_price: 900000,
          base_price: 780000,
        }),
      }),
    );
    await openPrices(user);
    await replaceText(user, input("Prix minimum"), "900000");
    await user.click(screen.getByRole("button", { name: "Enregistrer les prix" }));
    expect(
      await screen.findByText(
        `Le prix minimum (${money(900000)}) ne peut pas dépasser le prix de base (${money(780000)}).`,
      ),
    ).toBeVisible();
  });

  it("réglage « prix minimum » inactif : champ absent ; MIN_PRICE_DISABLED expliqué", async () => {
    const article = ownerArticle({ min_price: null, min_price_active: false });
    const { user } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [`GET ${API}/profile`]: json(200, profileBody("owner", false)),
        [GET]: json(200, article),
        [PUT]: apiError(422, "MIN_PRICE_DISABLED", "Désactivé", { field: "min_price" }),
      }),
    );
    expect(await screen.findByRole("region", { name: "Prix de vente" })).not.toHaveTextContent(
      "Prix minimum",
    );
    await openPrices(user);
    expect(screen.queryByLabelText("Prix minimum")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Enregistrer les prix" }));
    expect(await screen.findByText(MIN_DISABLED_MESSAGE)).toBeVisible();
  });

  it("conflit de version sur les prix : rechargement proposé", async () => {
    const { user } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [GET]: json(200, ownerArticle()),
        [PUT]: apiError(409, "VERSION_CONFLICT", "Version périmée"),
      }),
    );
    await openPrices(user);
    await user.click(screen.getByRole("button", { name: "Enregistrer les prix" }));
    expect(await screen.findByRole("button", { name: "Recharger l'article" })).toBeVisible();
  });
});

describe("archiver / réactiver (propriétaire)", () => {
  it("ARTICLE_HAS_STOCK : message clair, l'article reste actif", async () => {
    const { user } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [GET]: json(200, ownerArticle()),
        [ARCHIVE]: apiError(422, "ARTICLE_HAS_STOCK", "Stock", { article_id: HAOJUE_ID }),
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Archiver l'article" }));
    const dialog = screen.getByRole("dialog", { name: "Archiver « Haojue HJ125-8 » ?" });
    await user.click(within(dialog).getByRole("button", { name: "Archiver" }));
    expect(await screen.findByText(HAS_STOCK_MESSAGE)).toBeVisible();
    expect(screen.queryByText("Archivé")).toBeNull();
  });

  it("« Retour » ferme la confirmation sans rien envoyer", async () => {
    const { user, fake } = renderApp(
      SHEET,
      catalogRoutes("owner", { [GET]: json(200, ownerArticle()) }),
    );
    await user.click(await screen.findByRole("button", { name: "Archiver l'article" }));
    await user.click(screen.getByRole("button", { name: "Retour" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fake.count(ARCHIVE)).toBe(0);
  });

  it("archive puis réactive, avec confirmation et pastille « Archivé »", async () => {
    const archived = ownerArticle({ status: "archived", version: 4 });
    const { user } = renderApp(
      SHEET,
      catalogRoutes("owner", {
        [GET]: json(200, ownerArticle()),
        [ARCHIVE]: json(200, archived),
        [REACTIVATE]: json(200, ownerArticle({ version: 5 })),
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Archiver l'article" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Archiver" }));
    expect(await screen.findByText("Article archivé : Haojue HJ125-8")).toBeVisible();
    expect(screen.getByText("Archivé")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Réactiver l'article" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Réactiver" }));
    expect(await screen.findByText("Article réactivé : Haojue HJ125-8")).toBeVisible();
    expect(screen.getByRole("button", { name: "Archiver l'article" })).toBeVisible();
  });
});
