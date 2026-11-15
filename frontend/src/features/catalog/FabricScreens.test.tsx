import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { axeViolations } from "../../testing/axe";
import { API, catalogRoutes, listUrl, ownerArticle } from "../../testing/catalog";
import { json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { replaceText } from "../../testing/renderSale";
import { servedProfile } from "../../testing/servedProfile";

const STOCK = `/s/${SHOP_A}/stock`;
const PROFILE = `GET ${API}/profile`;
const FABRICS = `POST ${API}/articles/fabrics`;
const PATCH = `PATCH ${API}/articles/fabrics/Djampar`;
const COLORS = `POST ${API}/articles/fabrics/Djampar/colors`;
const OF_FABRIC = `GET ${API}/articles?status=active&limit=100&fabric=Djampar`;

configure({ asyncUtilTimeout: 5000 });
beforeEach(() => {
  window.localStorage.clear();
});

let next = 0;
/** Une couleur du tissu Djampar, telle que le serveur la crée (« Djampar — Rouge »). */
function color(name: string, overrides: Partial<ArticleResponse> = {}): ArticleResponse {
  next += 1;
  return ownerArticle({
    id: `01890a5d-ac96-774b-bcce-b3020000${String(next).padStart(4, "0")}`,
    display_name: `Djampar — ${name}`,
    brand: null,
    model: null,
    fabric: "Djampar",
    stock_unit: "METER",
    sold_by_piece: true,
    piece_length_m: "30.0",
    attributes: { color: name },
    base_price: 1500,
    base_price_piece: 40000,
    min_price: null,
    ...overrides,
  });
}

const input = (label: string) => {
  const field = screen.getByLabelText(label);
  if (!(field instanceof HTMLInputElement)) throw new Error(`« ${label} » n'est pas un champ`);
  return field;
};

const textile = (extra = {}) =>
  catalogRoutes("owner", { [PROFILE]: json(200, servedProfile("textile", "owner")), ...extra });

describe("tissus et couleurs (Textile, 2026-11-15)", () => {
  it("nouveau tissu : couleurs en saisie rapide, prix au mètre et au rouleau ; axe", async () => {
    const created = { fabric: "Djampar", items: [color("Rouge"), color("Bleu"), color("Vert")] };
    const { user, fake, container } = renderApp(
      `${STOCK}?article=nouveau-tissu`,
      textile({ [FABRICS]: json(201, created), [OF_FABRIC]: json(200, { items: created.items }) }),
    );
    await user.type(await screen.findByLabelText("Nom du tissu"), "Djampar");
    await user.click(screen.getByRole("button", { name: "Créer le tissu" }));
    expect(screen.getByText("Ajoutez au moins une couleur")).toBeVisible();
    expect(screen.getByText(/Indiquez la longueur d'un rouleau/)).toBeVisible();
    await user.type(input("Couleurs"), "rouge, Bleu ; vert, Rouge{Enter}");
    const chips = screen.getByRole("list", { name: "Couleurs ajoutées" });
    expect(
      within(chips)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["Rouge", "Bleu", "Vert"]);
    expect(screen.getByText(/3 articles seront créés/)).toHaveTextContent("Djampar — Rouge");
    await user.type(input("Longueur du rouleau"), "30");
    await replaceText(user, input("Prix au mètre (facultatif)"), "1500");
    await replaceText(user, input("Prix au rouleau (facultatif)"), "40000");
    expect(input("Minimum au rouleau (facultatif)")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Créer le tissu" }));
    await screen.findByText("Tissu créé : Djampar (3 couleurs)");
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === FABRICS)?.body).toMatchObject({
      fabric: "Djampar",
      colors: ["Rouge", "Bleu", "Vert"],
      roll_length_m: "30",
      meter_only: false,
      base_price: 1500,
      base_price_piece: 40000,
    });
    expect(await screen.findByRole("heading", { name: "Djampar", level: 1 })).toBeVisible();
  });

  it("« Au mètre seulement » : ni longueur ni prix du rouleau", async () => {
    const created = { fabric: "Getzner", items: [color("Blanc", { sold_by_piece: false })] };
    const { user, fake } = renderApp(
      `${STOCK}?article=nouveau-tissu`,
      textile({ [FABRICS]: json(201, created) }),
    );
    await user.type(await screen.findByLabelText("Nom du tissu"), "Getzner");
    await user.type(input("Couleurs"), "Blanc{Enter}");
    await user.click(screen.getByRole("switch", { name: /Au mètre seulement/ }));
    expect(screen.queryByLabelText("Longueur du rouleau")).toBeNull();
    expect(screen.queryByLabelText("Prix au rouleau (facultatif)")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Créer le tissu" }));
    await screen.findByText("Tissu créé : Getzner (1 couleur)");
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === FABRICS)?.body).toMatchObject({
      meter_only: true,
      roll_length_m: null,
      base_price_piece: null,
    });
  });

  it("page du tissu : modifier pour toutes les couleurs, ajouter une couleur", async () => {
    const colors = [color("Rouge"), color("Bleu")];
    const updated = colors.map((c) => ({ ...c, version: c.version + 1, base_price: 1600 }));
    const withJaune = [...updated, color("Jaune")];
    const { user, fake } = renderApp(
      `${STOCK}?tissu=Djampar`,
      textile({
        [OF_FABRIC]: json(200, { items: colors, next_cursor: null }),
        [PATCH]: json(200, { fabric: "Djampar", items: updated }),
        [COLORS]: json(201, { fabric: "Djampar", items: withJaune }),
      }),
    );
    const list = await screen.findByRole("list", { name: "Couleurs de Djampar" });
    expect(within(list).getAllByRole("button")).toHaveLength(2);
    const edit = within(screen.getByRole("form", { name: "Modifier le tissu" }));
    expect(edit.getByLabelText("Longueur du rouleau")).toHaveValue("30");
    await replaceText(user, edit.getByLabelText("Prix au mètre (facultatif)"), "1600");
    await user.click(edit.getByRole("button", { name: "Enregistrer le tissu" }));
    await screen.findByText("Djampar enregistré pour ses 2 couleurs");
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === PATCH)?.body).toMatchObject({
      roll_length_m: "30",
      prices: { base_price: 1600, base_price_piece: 40000 },
    });
    const add = within(screen.getByRole("region", { name: "Ajouter une couleur" }));
    await user.type(add.getByLabelText("Couleurs"), "rouge, jaune{Enter}"); // Rouge existe déjà
    await user.click(add.getByRole("button", { name: "Ajouter à Djampar" }));
    await screen.findByText("Couleur ajoutée à Djampar : Jaune");
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === COLORS)?.body).toEqual({
      colors: ["Jaune"],
    });
    expect(
      within(screen.getByRole("list", { name: "Couleurs de Djampar" })).getAllByRole("button"),
    ).toHaveLength(3);
  });

  it("liste des articles groupée par tissu, « Nouveau tissu » en tête", async () => {
    const items = [color("Rouge"), ownerArticle({ display_name: "Fil noir" }), color("Bleu")];
    const { user } = renderApp(
      `${STOCK}?vue=articles`,
      textile({ [listUrl()]: json(200, { items }) }),
    );
    const group = await screen.findByRole("region", { name: "Tissu Djampar" });
    expect(within(group).getByText("· 2 couleurs")).toBeVisible();
    expect(within(screen.getByRole("list", { name: "Autres articles" })).getByText("Fil noir"));
    expect(screen.getByRole("button", { name: "Nouveau tissu" })).toBeVisible();
    await user.click(within(group).getByRole("button", { name: "Voir le tissu Djampar" }));
    expect(await screen.findByRole("heading", { name: "Djampar", level: 1 })).toBeVisible();
  });
});
