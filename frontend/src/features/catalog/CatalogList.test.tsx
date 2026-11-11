import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  accountantArticle,
  catalogRoutes,
  listUrl,
  ownerArticle,
  typedSearch,
  YAMAHA_ID,
} from "../../testing/catalog";
import { json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { money } from "../../testing/renderSale";

const STOCK = `/s/${SHOP_A}/stock?vue=articles`;
const yamaha = (status = "active") =>
  ownerArticle({ id: YAMAHA_ID, display_name: "Yamaha Crypton", status, base_price: null });

// Premier rendu : écran chargé à la demande + restauration de session ; sous la charge de la
// suite complète, il dépasse parfois le délai d'attente par défaut (1 s) de Testing Library.
configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

const list = () => screen.findByRole("list", { name: "Articles trouvés" });

describe("liste des articles — propriétaire", () => {
  it("affiche les articles actifs, leur prix de base, et « Nouvel article »", async () => {
    const page = { items: [ownerArticle(), yamaha()], next_cursor: null };
    const { container } = renderApp(
      STOCK,
      catalogRoutes("owner", { [listUrl()]: json(200, page) }),
    );
    const rows = within(await list()).getAllByRole("button");
    expect(rows[0]).toHaveTextContent(`Haojue HJ125-8Prix de base : ${money(780000)}`);
    expect(rows[1]).toHaveTextContent("Yamaha CryptonPrix de base : non fixé");
    expect(screen.getByRole("button", { name: "Nouvel article" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Articles" })).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("cherche dès la première lettre (?q=) et dit quand rien ne correspond", async () => {
    const empty = json(200, { items: [], next_cursor: null });
    const found = json(200, { items: [ownerArticle()], next_cursor: null });
    const { user, fake } = renderApp(
      STOCK,
      catalogRoutes("owner", {
        [listUrl()]: json(200, { items: [ownerArticle(), yamaha()], next_cursor: null }),
        ...typedSearch("hao", found),
        ...typedSearch("zz", empty),
      }),
    );
    await list();
    await user.type(screen.getByLabelText("Rechercher un article"), "h");
    expect(fake.count(listUrl("h"))).toBe(1);
    await user.type(screen.getByLabelText("Rechercher un article"), "ao");
    expect(within(await list()).getAllByRole("button")).toHaveLength(1);
    await user.clear(screen.getByLabelText("Rechercher un article"));
    await user.type(screen.getByLabelText("Rechercher un article"), "zz");
    expect(await screen.findByText("Aucun article ne correspond à « zz ».")).toBeVisible();
  });

  it("filtre les archivés (pastille « Archivé ») puis tous", async () => {
    const { user } = renderApp(
      STOCK,
      catalogRoutes("owner", {
        [listUrl()]: json(200, { items: [ownerArticle()], next_cursor: null }),
        [listUrl(null, "archived")]: json(200, { items: [yamaha("archived")], next_cursor: null }),
        [listUrl(null, "all")]: json(200, { items: [], next_cursor: null }),
      }),
    );
    await list();
    await user.click(screen.getByRole("radio", { name: "Archivés" }));
    const row = within(await list()).getByRole("button", { name: /Yamaha Crypton/ });
    expect(within(row).getByText("Archivé")).toBeVisible();
    await user.click(screen.getByRole("radio", { name: "Tous" }));
    expect(await screen.findByText("Aucun article pour l'instant.")).toBeVisible();
  });

  it("« Afficher plus » ajoute la page suivante (curseur)", async () => {
    const { user } = renderApp(
      STOCK,
      catalogRoutes("owner", {
        [listUrl()]: json(200, { items: [ownerArticle()], next_cursor: "c2" }),
        [listUrl(null, "active", "c2")]: json(200, { items: [yamaha()], next_cursor: null }),
      }),
    );
    await list();
    await user.click(screen.getByRole("button", { name: "Afficher plus" }));
    expect(await screen.findByRole("button", { name: /Yamaha Crypton/ })).toBeVisible();
    expect(within(await list()).getAllByRole("button")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Afficher plus" })).toBeNull();
  });

  it("ouvre la fiche d'un article", async () => {
    const { user, router } = renderApp(
      STOCK,
      catalogRoutes("owner", {
        [listUrl()]: json(200, { items: [ownerArticle()], next_cursor: null }),
        [`GET /api/v1/shops/${SHOP_A}/articles/${ownerArticle().id}`]: json(200, ownerArticle()),
      }),
    );
    await user.click(within(await list()).getByRole("button", { name: /Haojue/ }));
    expect(router.state.location.search).toBe(`?article=${ownerArticle().id}`);
    expect(await screen.findByRole("heading", { name: "Haojue HJ125-8" })).toBeVisible();
  });

  it("hors connexion : le dit et propose de réessayer", async () => {
    const { user } = renderApp(
      STOCK,
      catalogRoutes("owner", {
        [listUrl()]: [
          new TypeError("Failed to fetch"),
          json(200, { items: [], next_cursor: null }),
        ],
      }),
    );
    expect(
      await screen.findByText("Connexion nécessaire pour afficher les articles."),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Aucun article pour l'instant.")).toBeVisible();
  });
});

describe("liste des articles — autres rôles", () => {
  it("comptable : le CMP, jamais de prix de vente", async () => {
    const page = { items: [accountantArticle()], next_cursor: null };
    renderApp(STOCK, catalogRoutes("accountant", { [listUrl()]: json(200, page) }));
    const row = within(await list()).getByRole("button", { name: /Haojue/ });
    expect(row).toHaveTextContent("Coût moyen (CMP) : non calculable");
    expect(screen.queryByText(/Prix de base/)).toBeNull();
    expect(screen.getByRole("button", { name: "Nouvel article" })).toBeVisible();
  });

  it("vendeur : « Stock » n'ouvre pas la gestion du catalogue (aucun appel aux articles)", async () => {
    // Le vendeur arrive sur la matrice de stock (module Stock), jamais sur le catalogue.
    const emptyStock = json(200, { locations: [], items: [] });
    const { fake } = renderApp(
      STOCK,
      catalogRoutes("seller", { [`GET /api/v1/shops/${SHOP_A}/stock?sort=name`]: emptyStock }),
    );
    expect(await screen.findByText("Aucun article en stock pour l'instant.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Nouvel article" })).toBeNull();
    expect(fake.calls.some((call) => call.url.includes("/articles"))).toBe(false);
  });

  it("chauffeur : la section n'existe pas pour lui", async () => {
    const { fake } = renderApp(STOCK, catalogRoutes("driver"));
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
    expect(fake.calls.some((call) => call.url.includes("/articles"))).toBe(false);
  });
});
