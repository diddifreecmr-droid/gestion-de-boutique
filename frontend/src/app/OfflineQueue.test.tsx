/**
 * File hors connexion dans la coquille (droit actif, configuration de test) : compteur « N
 * saisies en attente d'envoi », saisie refusée visible avec son motif (RG-T23, OFF-07),
 * déconnexion bloquée sauf double confirmation (RG-T24, OFF-08).
 */
import "fake-indexeddb/auto";
import { screen, within } from "@testing-library/react";
import { Dexie } from "dexie";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { DB_NAME } from "../core/offline/db";
import { openOutbox } from "../core/offline/engine";
import { RIGHTS_KEY } from "../core/offline/rights";
import { ALL_MODULES } from "../core/profile/modules";
import { PROFILE_KEY } from "../core/profile/savedProfiles";
import { servedProfile } from "../testing/servedProfile";
import { json, meBody, ROUTES, SHOP_A, tokenBody } from "../testing/fakeApi";
import { renderApp } from "../testing/renderApp";

const API = `/api/v1/shops/${SHOP_A}`;
const offline = new TypeError("Failed to fetch");

beforeEach(async () => {
  window.localStorage.setItem(RIGHTS_KEY, JSON.stringify([SHOP_A]));
  // Hors connexion, la coquille ouvre la boutique avec le profil gardé (meBody : vendeur).
  const profile = servedProfile("motos", "seller", ALL_MODULES);
  window.localStorage.setItem(PROFILE_KEY, JSON.stringify({ [SHOP_A]: profile }));
  const outbox = openOutbox();
  const base = { shopId: SHOP_A, type: "sale.create" as const, capturedAt: "", payload: {} };
  await outbox.enqueue({ ...base, opId: "op-1", provisionalNumber: "V-HL-3F2A-0001" });
  await outbox.enqueue({ ...base, opId: "op-2", provisionalNumber: "V-HL-3F2A-0002" });
  await outbox.reject("op-2", { code: "PRICE_BELOW_MINIMUM", message: "Prix sous le minimum" });
  outbox.db.close();
});

afterEach(async () => {
  window.localStorage.clear();
  await Dexie.delete(DB_NAME);
});

function openAccount() {
  return renderApp(`/s/${SHOP_A}/compte`, {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(200, meBody()),
    [ROUTES.logout]: new Response(null, { status: 204 }),
    [`GET ${API}/profile`]: offline,
    [`POST ${API}/sync`]: offline,
    [`GET ${API}/offline-snapshot`]: offline,
  });
}

describe("file hors connexion (droit actif)", () => {
  it("compteur, refus visible avec motif ; envoi tenté à l'ouverture", async () => {
    const { fake } = openAccount();
    const counter = await screen.findByText("1 saisie en attente d'envoi");
    expect(counter).toBeVisible();
    expect(screen.getByText("Saisie V-HL-3F2A-0002 refusée")).toBeVisible();
    expect(screen.getByText("Prix sous le minimum")).toBeVisible();
    expect(fake.count(`POST ${API}/sync`)).toBe(1);
  });

  it("déconnexion : bloquée, puis double confirmation avant de perdre la file", async () => {
    const { user, fake } = openAccount();
    await screen.findByText("Saisie V-HL-3F2A-0002 refusée");
    await user.click(screen.getByRole("button", { name: "Se déconnecter" }));
    const first = await screen.findByRole("dialog", { name: "1 saisie en attente d'envoi" });
    await user.click(within(first).getByRole("button", { name: "Retour" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fake.count(ROUTES.logout)).toBe(0);

    await user.click(screen.getByRole("button", { name: "Se déconnecter" }));
    const again = await screen.findByRole("dialog", { name: "1 saisie en attente d'envoi" });
    await user.click(within(again).getByRole("button", { name: "Se déconnecter quand même" }));
    const second = screen.getByRole("dialog", { name: "Perdre définitivement 1 saisie ?" });
    await user.click(within(second).getByRole("button", { name: "Oui, perdre les saisies" }));
    await screen.findByRole("button", { name: "Se connecter" });
    expect(fake.count(ROUTES.logout)).toBe(1);
    const outbox = openOutbox();
    expect(await outbox.waiting()).toBe(0);
    outbox.db.close();
  });
});
