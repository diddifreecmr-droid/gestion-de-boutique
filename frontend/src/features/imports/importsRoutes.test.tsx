import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { memberSession, SHOP_PATH } from "../../testing/lot1Screens";
import { renderApp } from "../../testing/renderApp";
import { IMPORTS_KEY } from "./importsNav";

/**
 * Le module `import` est « à venir » (T46) : la coquille l'écarte, même servi actif. Pour
 * tester l'écran, `forceUpcoming` fait garder les modules à venir servis par le faux serveur.
 */
const flags = vi.hoisted(() => ({ forceUpcoming: false }));

vi.mock("../../core/profile/modules", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../core/profile/modules")>();
  return {
    ...original,
    shopModules: (codes: readonly string[]) => {
      if (!flags.forceUpcoming) return original.shopModules(codes);
      const enabled = new Set([...original.ALWAYS_ON, ...codes.map(original.parseModule)]);
      return { enabled, has: (module: string) => enabled.has(module as never) };
    },
  };
});

beforeAll(async () => {
  await import("./ImportsRoute");
});

const PATH = `${SHOP_PATH}/${IMPORTS_KEY}`;

describe("adresse de l'import (on ne montre jamais ce qui n'existe pas)", () => {
  it("module à venir servi actif par le serveur : écran introuvable", async () => {
    flags.forceUpcoming = false;
    renderApp(PATH, memberSession("owner"));
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });

  it("module `import` forcé actif : le propriétaire ouvre l'import ; axe", async () => {
    flags.forceUpcoming = true;
    const { container } = renderApp(PATH, memberSession("owner"));
    expect(await screen.findByRole("heading", { name: "Import Excel" })).toBeVisible();
    const models = screen.getByRole("list", { name: "Modèles d'import" });
    expect(within(models).getAllByRole("button")).toHaveLength(5);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("module forcé actif : le comptable a 3 modèles, le vendeur n'a pas d'écran", async () => {
    flags.forceUpcoming = true;
    const accountant = renderApp(PATH, memberSession("accountant"));
    const models = await screen.findByRole("list", { name: "Modèles d'import" });
    expect(within(models).getAllByRole("button")).toHaveLength(3);
    accountant.unmount();
    renderApp(PATH, memberSession("seller"));
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });
});
