import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  apiError,
  json,
  meBody,
  ROUTES,
  SHOP_A,
  tokenBody,
  type Reply,
} from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { formatTime } from "../../shared/format";
import { PIN_TOO_SIMPLE_MESSAGE } from "./changePinErrors";

function openChangePin(changePin: Reply | Reply[], admin = false) {
  const first = meBody({
    must_change_pin: true,
    is_platform_admin: admin,
    ...(admin ? { shops: [] } : {}),
  });
  return renderApp("/changer-code", {
    [ROUTES.refresh]: json(200, tokenBody("t1", true)),
    [ROUTES.me]: [json(200, first), json(200, { ...first, must_change_pin: false })],
    [ROUTES.changePin]: changePin,
    [ROUTES.logout]: new Response(null, { status: 204 }),
  });
}

async function submit(
  user: ReturnType<typeof openChangePin>["user"],
  current: string,
  next: string,
  confirmation = next,
) {
  await user.type(await screen.findByLabelText("Code actuel"), current);
  await user.type(screen.getByLabelText(/^Nouveau code$/), next);
  await user.type(screen.getByLabelText("Nouveau code, encore une fois"), confirmation);
  await user.click(screen.getByRole("button", { name: "Changer mon code" }));
}

describe("changement de code (UC-SOC-07)", () => {
  it("trois champs à 6 chiffres, première connexion expliquée ; aucune violation axe", async () => {
    const { container } = openChangePin(new Response(null, { status: 204 }));
    expect(await screen.findByText(/Première connexion/)).toBeVisible();
    for (const label of ["Code actuel", "Nouveau code, encore une fois"]) {
      expect(screen.getByLabelText(label)).toHaveAttribute("inputmode", "numeric");
    }
    expect(await axeViolations(container)).toEqual([]);
  });

  it("refuse deux saisies différentes avant l'envoi", async () => {
    const { user, fake } = openChangePin(new Response(null, { status: 204 }));
    await submit(user, "482915", "582914", "582915");
    expect(screen.getByText("Les deux saisies du nouveau code diffèrent")).toBeVisible();
    expect(fake.count(ROUTES.changePin)).toBe(0);
  });

  it("code trop simple → refus affiché sur le nouveau code ; aucune violation axe", async () => {
    const { user, container } = openChangePin(
      apiError(422, "PIN_TOO_SIMPLE", "Code trop simple", { reason: "sequence" }),
    );
    await submit(user, "482915", "123456");
    expect(await screen.findByText(PIN_TOO_SIMPLE_MESSAGE)).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("code actuel faux (422) → « encore N essais », sans déconnexion ni refresh", async () => {
    const { user, fake } = openChangePin(
      apiError(422, "CURRENT_PIN_INVALID", "Code actuel incorrect", { remaining_attempts: 2 }),
    );
    await submit(user, "000111", "582914");
    expect(await screen.findByText("Code actuel incorrect — encore 2 essais")).toBeVisible();
    expect(fake.count(ROUTES.refresh)).toBe(1);
  });

  it("5 codes faux (423 PIN_CHANGE_LOCKED) → heure de fin, toujours connecté", async () => {
    const { user, router } = openChangePin(
      apiError(423, "PIN_CHANGE_LOCKED", "Bloqué", { until: "2026-11-11T13:32:00+00:00" }),
    );
    await submit(user, "000111", "582914");
    // textContent brut : les espaces insécables de « 14 h 32 » sont vérifiées telles quelles.
    expect((await screen.findByText(/^Changement de code bloqué/)).textContent).toContain(
      `Changement de code bloqué jusqu'à ${formatTime("2026-11-11T13:32:00Z")}`,
    );
    expect(router.state.location.pathname).toBe("/changer-code");
  });

  it("succès → message, retour à l'accueil, plus de redirection forcée", async () => {
    const { user, router, fake } = openChangePin(new Response(null, { status: 204 }));
    await submit(user, "482915", "582914");
    expect(await screen.findByText("Code changé")).toBeVisible();
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/s/${SHOP_A}`);
    });
    expect(fake.calls.find((c) => c.url.endsWith("/change-pin"))?.body).toEqual({
      current_pin: "482915",
      new_pin: "582914",
      new_pin_confirmation: "582914",
    });
  });

  it("administrateur : mot de passe (10 caractères au moins)", async () => {
    const { user } = openChangePin(new Response(null, { status: 204 }), true);
    await user.type(await screen.findByLabelText("Mot de passe actuel"), "ancien");
    await user.click(screen.getByRole("button", { name: "Changer mon mot de passe" }));
    expect(screen.getAllByText("Le mot de passe doit avoir au moins 10 caractères")).toHaveLength(
      1,
    );
  });

  it("depuis l'écran imposé, on peut se déconnecter", async () => {
    const { user, router } = openChangePin(new Response(null, { status: 204 }));
    await user.click(await screen.findByRole("button", { name: "Se déconnecter" }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/connexion");
    });
  });
});
