/**
 * Console : la liste envoyée au `PATCH` est **complète**, obligatoires compris (le serveur refuse
 * une liste incomplète, `422 MODULE_MANDATORY`) ; refus de modules dits en français (§ 4.5).
 */
import { screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { ApiError } from "../../core/api/errors";
import { ALWAYS_ON } from "../../core/profile/modules";
import { axeViolations } from "../../testing/axe";
import { apiError, json, type Reply } from "../../testing/fakeApi";
import {
  ADMIN_SHOP_ID,
  adminSession,
  PLATFORM,
  preloadLot1Screens,
  shopAccess,
  shopSummary,
} from "../../testing/lot1Screens";
import { renderApp } from "../../testing/renderApp";
import { moduleRefusal } from "./moduleRefusals";

beforeAll(preloadLot1Screens);

const ONE = `${PLATFORM}/${ADMIN_SHOP_ID}`;

function openSheet(enabled: string[], patch: Reply | Reply[] = json(200, shopSummary())) {
  return renderApp(`/plateforme?id=${ADMIN_SHOP_ID}`, {
    ...adminSession(),
    [`GET ${ONE}`]: json(200, shopSummary({ enabled_modules: enabled })),
    [`GET ${ONE}/access`]: json(200, shopAccess()),
    [`PATCH ${ONE}`]: patch,
  });
}

const saveButton = () => screen.getByRole("button", { name: "Enregistrer les modules" });

describe("console — liste complète des modules au PATCH", () => {
  it("boutique lue sans ses modules obligatoires : ils sont quand même envoyés", async () => {
    const { user, fake } = openSheet(["core", "purchases"]);
    await user.click(await screen.findByRole("switch", { name: "Dépenses" }));
    await user.click(saveButton());
    const body = fake.calls.find((c) => c.method === "PATCH")?.body as { modules: string[] };
    expect(body.modules).toEqual([...ALWAYS_ON, "purchases", "expenses"]);
  });

  it("tout désactiver : seuls les obligatoires partent, jamais une liste vide", async () => {
    const { user, fake } = openSheet([...ALWAYS_ON, "purchases", "dashboard"]);
    await user.click(await screen.findByRole("switch", { name: "Achats" }));
    await user.click(screen.getByRole("switch", { name: "Tableau de bord" }));
    await user.click(saveButton());
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({ modules: ALWAYS_ON });
  });

  it("refus 422 MODULE_MANDATORY : message clair, la fiche reste ; axe", async () => {
    const { user, container } = openSheet(
      [...ALWAYS_ON],
      apiError(422, "MODULE_MANDATORY", "Module obligatoire", { module: "sales" }),
    );
    await user.click(await screen.findByRole("switch", { name: "Achats" }));
    await user.click(saveButton());
    expect(
      await screen.findByText(
        "Le module « Ventes et reçus » est toujours actif : il ne peut pas être retiré. Rien n'a été enregistré.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Motos Garoua" })).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });
});

describe("moduleRefusal", () => {
  const refusal = (code: string, details: Record<string, unknown> = {}) =>
    moduleRefusal(new ApiError(422, code, "x", details));

  it("détails absents ou inconnus : phrase générale, sans code technique", () => {
    expect(refusal("MODULE_MANDATORY")).toBe(
      "Un module toujours actif manque : la boutique ne peut pas s'en passer. Rien n'a été enregistré.",
    );
    expect(refusal("MODULE_DEPENDENCY", { module: "transport", requires: "bateau" })).toBe(
      "Un module a besoin d'un autre module qui n'est pas activé. Rien n'a été enregistré.",
    );
  });

  it("une autre erreur n'est pas un refus de modules", () => {
    expect(refusal("VALIDATION_ERROR")).toBeUndefined();
  });
});
