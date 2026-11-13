import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../../testing/axe";
import { renderApp } from "../../../testing/renderApp";
import { preloadSettings, route, settingsRoutes, viewPath } from "../../../testing/shopSettingsApi";
import { WAREHOUSE_WARNING } from "./LocationFields";

beforeAll(preloadSettings);
beforeEach(() => {
  window.localStorage.clear();
});

describe("Lieux : avertissement d'entrepôt (QC-5, LOC-01)", () => {
  it("choisir « Entrepôt » avertit avant l'envoi ; « Boutique » le retire ; axe", async () => {
    const { user, fake, container } = renderApp(viewPath("lieux"), settingsRoutes("owner"));
    await screen.findByRole("list", { name: "Lieux de la boutique" });
    expect(screen.queryByText(WAREHOUSE_WARNING)).toBeNull();
    const kind = screen.getByRole("radiogroup", { name: "Nouveau lieu — type" });
    await user.click(within(kind).getByRole("radio", { name: "Entrepôt" }));
    expect(screen.getByText(WAREHOUSE_WARNING)).toBeVisible();
    expect(screen.getByText(/Déplacement disponible plus tard/)).toBeVisible();
    expect(fake.count(route("POST", "/locations"))).toBe(0);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(kind).getByRole("radio", { name: "Boutique" }));
    expect(screen.queryByText(WAREHOUSE_WARNING)).toBeNull();
  });
});
