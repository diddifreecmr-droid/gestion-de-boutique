import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../../testing/axe";
import { apiError, json, type Call } from "../../../testing/fakeApi";
import { renderApp } from "../../../testing/renderApp";
import {
  member,
  preloadSettings,
  route,
  SELLER_ID,
  settingsRoutes,
  viewPath,
} from "../../../testing/shopSettingsApi";
import { SELF_LOCKED } from "./MemberActions";

const PATH = viewPath("membres");
const ONE = `/members/${SELLER_ID}`;

beforeAll(preloadSettings);
beforeEach(() => {
  window.localStorage.clear();
});

const bodyOf = (calls: readonly Call[], key: string) =>
  calls.find((c) => `${c.method} ${c.url}` === key)?.body;

const rowOf = (name: string) => {
  const list = screen.getByRole("list", { name: "Membres de la boutique" });
  const row = within(list).getByText(name).closest("li");
  if (row === null) throw new Error(`Membre « ${name} » absent`);
  return within(row);
};

const openMembers = async (routes = settingsRoutes("owner")) => {
  const view = renderApp(PATH, routes);
  await screen.findByRole("list", { name: "Membres de la boutique" });
  return view;
};

describe("Membres (UC-SOC-04, MEM-01 à 04)", () => {
  it("liste : rôle et lieu habituel ; ses propres accès ne se coupent pas ; axe", async () => {
    const { container } = await openMembers();
    expect(rowOf("Moussa Hamadou").getByText(/Vendeur · Garoua/)).toBeVisible();
    expect(rowOf("Awa Bello").getByText("Vous")).toBeVisible();
    const own = rowOf("Awa Bello").getByRole("button", { name: "Désactiver" });
    expect(own).toHaveAttribute("aria-disabled", "true");
    expect(own).toHaveAccessibleDescription(SELF_LOCKED);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("ajoute un vendeur : champs vérifiés, lieu présélectionné, code provisoire montré une fois", async () => {
    const add = route("POST", "/members");
    const created = member({ user_id: "u-new", name: "Ali Oumarou", phone: "+237690000001" });
    const { user, fake, container } = await openMembers({
      ...settingsRoutes("owner"),
      [add]: json(201, { member: created, temporary_pin: "418273", existing_account: false }),
    });
    await user.click(screen.getByRole("button", { name: "Ajouter le membre" }));
    expect(screen.getByText("Le nom est vide")).toBeVisible();
    expect(screen.getByText("Le téléphone est vide")).toBeVisible();
    expect(fake.count(add)).toBe(0);

    await user.type(screen.getByLabelText("Nouveau membre — nom"), "Ali Oumarou");
    await user.type(screen.getByLabelText(/Nouveau membre — téléphone/), "690000001");
    const place = screen.getByRole("radiogroup", {
      name: "Nouveau membre — lieu de vente habituel",
    });
    expect(within(place).getByRole("radio", { name: "Garoua" })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Ajouter le membre" }));

    expect(await screen.findByText("418273")).toBeVisible();
    expect(bodyOf(fake.calls, add)).toEqual({
      name: "Ali Oumarou",
      phone: "690000001",
      role: "seller",
      default_location_id: "loc-garoua",
    });
    expect(rowOf("Ali Oumarou").getByText(/Vendeur/)).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "J'ai noté le code" }));
    expect(screen.queryByText("418273")).toBeNull();
  });

  it("ajoute un comptable au compte existant : pas de lieu, pas de code ; doublon refusé", async () => {
    const add = route("POST", "/members");
    const created = member({ user_id: "u-acc", name: "Paul Ndam", role: "accountant" });
    const { user, fake } = await openMembers({
      ...settingsRoutes("owner"),
      [add]: [
        json(201, {
          member: { ...created, default_location_id: null },
          temporary_pin: null,
          existing_account: true,
        }),
        apiError(409, "DUPLICATE", "déjà membre"),
      ],
    });
    await user.type(screen.getByLabelText("Nouveau membre — nom"), "Paul Ndam");
    await user.type(screen.getByLabelText(/Nouveau membre — téléphone/), "677000003");
    await user.click(screen.getByRole("radio", { name: "Comptable" }));
    expect(screen.queryByRole("radiogroup", { name: /lieu de vente habituel/ })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Ajouter le membre" }));
    expect(
      await screen.findByText("Paul Ndam avait déjà un compte : il garde son code."),
    ).toBeVisible();
    expect(bodyOf(fake.calls, add)).toMatchObject({
      role: "accountant",
      default_location_id: null,
    });

    await user.type(screen.getByLabelText("Nouveau membre — nom"), "Paul Ndam");
    await user.type(screen.getByLabelText(/Nouveau membre — téléphone/), "677000003");
    await user.click(screen.getByRole("button", { name: "Ajouter le membre" }));
    expect(
      await screen.findByText("Ce nom ou ce numéro existe déjà dans la boutique."),
    ).toBeVisible();
  });

  it("change le rôle d'un vendeur en chauffeur (lieu effacé) ; refus du serveur expliqué", async () => {
    const patch = route("PATCH", ONE);
    const { user, fake } = await openMembers({
      ...settingsRoutes("owner"),
      [patch]: [
        apiError(409, "VERSION_CONFLICT", "x"),
        json(200, member({ role: "driver", default_location_id: null, version: 2 })),
      ],
    });
    await user.click(rowOf("Moussa Hamadou").getByRole("button", { name: "Changer le rôle" }));
    const roles = screen.getByRole("radiogroup", {
      name: "Changer le rôle de Moussa Hamadou — rôle",
    });
    await user.click(within(roles).getByRole("radio", { name: "Chauffeur" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText(/modifié cet élément entre-temps/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await rowOf("Moussa Hamadou").findByText(/Chauffeur/)).toBeVisible();
    expect(bodyOf(fake.calls, patch)).toEqual({
      role: "driver",
      default_location_id: null,
      version: 1,
    });
  });

  it("désactiver demande une confirmation ; réactiver ne la demande pas", async () => {
    const patch = route("PATCH", ONE);
    const { user, fake } = await openMembers({
      ...settingsRoutes("owner"),
      [patch]: [
        json(200, member({ active: false, version: 2 })),
        json(200, member({ active: true, version: 3 })),
      ],
    });
    await user.click(rowOf("Moussa Hamadou").getByRole("button", { name: "Désactiver" }));
    const dialog = screen.getByRole("dialog", { name: "Désactiver Moussa Hamadou ?" });
    expect(fake.count(patch)).toBe(0);
    await user.click(within(dialog).getByRole("button", { name: "Désactiver" }));
    expect(await rowOf("Moussa Hamadou").findByText("Désactivé")).toBeVisible();
    expect(fake.calls.filter((c) => `${c.method} ${c.url}` === patch)[0]?.body).toEqual({
      active: false,
      version: 1,
    });
    await user.click(rowOf("Moussa Hamadou").getByRole("button", { name: "Réactiver" }));
    expect(
      await rowOf("Moussa Hamadou").findByRole("button", { name: "Désactiver" }),
    ).toBeVisible();
    expect(fake.calls.filter((c) => `${c.method} ${c.url}` === patch)[1]?.body).toEqual({
      active: true,
      version: 2,
    });
  });
});
