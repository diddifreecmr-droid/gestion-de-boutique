import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { json } from "../../../testing/fakeApi";
import { renderApp } from "../../../testing/renderApp";
import { OFFLINE_MESSAGE } from "../settingsErrors";
import {
  member,
  MEMBERS,
  OWNER_ID,
  preloadSettings,
  route,
  SELLER_ID,
  settingsRoutes,
  viewPath,
} from "../../../testing/shopSettingsApi";

const PATH = viewPath("membres");
const ONE = `/members/${SELLER_ID}`;

beforeAll(preloadSettings);
beforeEach(() => {
  window.localStorage.clear();
});

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

describe("Membres — accès au compte (décision du 11/11/2026 : compte entier)", () => {
  it("compte bloqué : débloquer, redonner un code (affiché), déconnecter les appareils", async () => {
    const locked = member({ locked: true });
    const unlock = route("POST", `${ONE}/unlock`);
    const reset = route("POST", `${ONE}/reset-pin`);
    const revoke = route("POST", `${ONE}/revoke-devices`);
    const { user, fake } = await openMembers({
      ...settingsRoutes("owner"),
      [route("GET", "/members")]: json(200, [MEMBERS[0], locked]),
      [unlock]: new Response(null, { status: 204 }),
      [reset]: json(200, { temporary_pin: "902615" }),
      [revoke]: json(200, { revoked_sessions: 2 }),
    });
    expect(rowOf("Moussa Hamadou").getByText("Bloqué")).toBeVisible();
    await user.click(rowOf("Moussa Hamadou").getByRole("button", { name: "Débloquer" }));
    expect(await screen.findByText("Moussa Hamadou est débloqué.")).toBeVisible();
    expect(rowOf("Moussa Hamadou").queryByText("Bloqué")).toBeNull();
    expect(fake.count(unlock)).toBe(1);

    await user.click(rowOf("Moussa Hamadou").getByRole("button", { name: "Redonner un code" }));
    const dialog = screen.getByRole("dialog", { name: "Redonner un code à Moussa Hamadou ?" });
    await user.click(within(dialog).getByRole("button", { name: "Redonner un code" }));
    expect(await screen.findByText("902615")).toBeVisible();
    expect(rowOf("Moussa Hamadou").getByText("Code provisoire")).toBeVisible();

    await user.click(
      rowOf("Moussa Hamadou").getByRole("button", { name: "Déconnecter ses appareils" }),
    );
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Déconnecter" }),
    );
    expect(await screen.findByText("Moussa Hamadou : 2 appareils déconnectés.")).toBeVisible();
    expect(fake.count(route("PATCH", `/members/${OWNER_ID}`))).toBe(0);
  });

  it("coupure réseau pendant « Redonner un code » : rien n'est montré, le message le dit", async () => {
    const { user } = await openMembers({
      ...settingsRoutes("owner"),
      [route("POST", `${ONE}/reset-pin`)]: new TypeError("Failed to fetch"),
    });
    await user.click(rowOf("Moussa Hamadou").getByRole("button", { name: "Redonner un code" }));
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Redonner un code" }),
    );
    expect(await screen.findByText(OFFLINE_MESSAGE)).toBeVisible();
    expect(screen.queryByRole("region", { name: /Code provisoire/ })).toBeNull();
  });
});
