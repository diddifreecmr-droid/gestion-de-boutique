/**
 * VOC-01 (T39) : les écrans principaux d'une boutique Prêt-à-porter ou Textile ne parlent
 * jamais de Motos. Le DOM entier (contenu replié compris) est balayé une fois l'écran chargé.
 */
import { configure, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { apparelShop, ARTICLE_ID, type ApparelCode, type ShopRole } from "../testing/apparelShop";
import { SHOP_A } from "../testing/fakeApi";
import { renderApp } from "../testing/renderApp";
import { preloadDashboard } from "../testing/dashboard";
import { articleButton, preloadSales } from "../testing/renderSale";

configure({ asyncUtilTimeout: 5000 });

beforeAll(async () => {
  await Promise.all([preloadDashboard(), preloadSales(), import("../features/stock/StockRoute")]);
});
beforeEach(() => {
  window.localStorage.clear();
});

/** Mots du profil Motos interdits ailleurs (recette Lot 3, VOC-01). */
const FORBIDDEN = /mod[eè]le|ch[aâ]ssis|garoua|vendeur|camion/i;
const ARTICLE_NAME: Record<ApparelCode, string> = {
  apparel: "Chemise lin",
  textile: "Wax Fleur de mariage",
};

const SHOP = `/s/${SHOP_A}`;
interface Screen {
  name: string;
  path: string;
  /** Attend l'écran chargé (texte propre à l'écran). */
  ready: (code: ApparelCode) => Promise<unknown>;
  /** Ouvre ce qui est replié et doit être balayé aussi (filtres). */
  open?: (user: ReturnType<typeof renderApp>["user"]) => Promise<void>;
}

const heading = (name: string | RegExp) => () => screen.findByRole("heading", { name });
const article = (code: ApparelCode) => screen.findAllByText(ARTICLE_NAME[code]);

const SCREENS: Record<ShopRole, Screen[]> = {
  owner: [
    { name: "accueil", path: SHOP, ready: () => screen.findAllByText("Ventes du jour") },
    {
      name: "tableau de bord",
      path: `${SHOP}/tableau-de-bord`,
      ready: () => screen.findByText("Erreurs signalées par les employés"),
    },
    {
      name: "ventes (filtres ouverts)",
      path: `${SHOP}/ventes`,
      ready: async () => {
        await screen.findByRole("heading", { name: "Ventes" });
        await screen.findByRole("button", { name: /^Filtres/ });
      },
      open: async (user) => {
        await user.click(screen.getByRole("button", { name: /^Filtres/ }));
        expect(await screen.findByRole("radiogroup", { name: "Employé" })).toBeVisible();
        expect(screen.getByRole("radio", { name: "Tous les employés" })).toBeVisible();
      },
    },
    { name: "nouvelle vente", path: `${SHOP}/nouvelle-vente`, ready: heading("Nouvelle vente") },
    { name: "stock", path: `${SHOP}/stock`, ready: article },
    { name: "articles", path: `${SHOP}/stock?vue=articles`, ready: article },
    { name: "fiche article", path: `${SHOP}/stock?article=${ARTICLE_ID}`, ready: article },
  ],
  seller: [
    { name: "accueil", path: SHOP, ready: () => screen.findAllByText("Ventes du jour") },
    { name: "mes ventes", path: `${SHOP}/mes-ventes`, ready: heading("Mes ventes") },
    { name: "nouvelle vente", path: `${SHOP}/nouvelle-vente`, ready: heading("Nouvelle vente") },
    { name: "stock", path: `${SHOP}/stock`, ready: article },
    { name: "fiche article", path: `${SHOP}/stock?article=${ARTICLE_ID}`, ready: article },
  ],
};

async function settled(): Promise<void> {
  await waitFor(() => {
    expect(screen.queryByText(/^(Chargement|Ouverture|Préparation)/)).toBeNull();
  });
}

function forbiddenIn(container: HTMLElement): string[] {
  const text = container.textContent;
  const labels = [...container.querySelectorAll("[aria-label],[placeholder],[title]")].map(
    (element) =>
      ["aria-label", "placeholder", "title"]
        .map((name) => element.getAttribute(name) ?? "")
        .join(" "),
  );
  return [text, ...labels].flatMap((chunk) => chunk.match(new RegExp(FORBIDDEN, "gi")) ?? []);
}

/** Aide de la recherche d'article du Stock, tirée des champs du profil. */
const STOCK_HINT: Record<ApparelCode, string> = {
  apparel: "Nom, référence ou marque",
  textile: "Nom ou référence",
};

describe.each<ApparelCode>(["apparel", "textile"])("VOC-01 — profil %s", (code) => {
  for (const role of ["owner", "seller"] as const) {
    for (const shown of SCREENS[role]) {
      it(`${role} · ${shown.name} : aucun mot du profil Motos`, async () => {
        const { container, user } = renderApp(shown.path, apparelShop(code, role));
        await shown.ready(code);
        await settled();
        await shown.open?.(user);
        expect(forbiddenIn(container)).toEqual([]);
      });
    }
  }

  it("stock : la recherche parle des champs du profil", async () => {
    renderApp(`${SHOP}/stock`, apparelShop(code, "owner"));
    expect(await screen.findByLabelText("Rechercher un article")).toHaveAccessibleDescription(
      STOCK_HINT[code],
    );
  });
});

describe("VOC-01 — nouvelle vente Prêt-à-porter : détails de l'article du profil", () => {
  it("article ajouté : taille et couleur sur la ligne (panier), ni châssis ni moteur", async () => {
    const { user, container } = renderApp(
      `${SHOP}/nouvelle-vente`,
      apparelShop("apparel", "seller"),
    );
    await screen.findByRole("heading", { name: "Nouvelle vente" });
    await user.click(await articleButton(ARTICLE_NAME.apparel));
    await screen.findByRole("heading", { name: ARTICLE_NAME.apparel });
    // Panier (T40) : taille et couleur en choix rapides, pas de « Détails de l'article » par unité.
    expect(screen.queryByRole("button", { name: "Détails de l'article" })).toBeNull();
    expect(screen.getAllByText("Couleur")[0]).toBeVisible();
    expect(screen.queryByLabelText(/moteur|châssis/i)).toBeNull();
    expect(forbiddenIn(container)).toEqual([]);
  });
});
