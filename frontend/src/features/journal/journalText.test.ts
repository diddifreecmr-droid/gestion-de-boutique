import { describe, expect, it } from "vitest";
import { entry } from "../../testing/lot1Screens";
import { ALL, NO_FILTERS, toQuery } from "./journalFilters";
import { changeValue, entrySentence, moduleLabel, type People } from "./journalText";

const people: People = {
  nameOf: (id) => (id === "u-1" ? "Paul" : undefined),
  roleLabel: (role) => (role === "seller" ? "Vendeur" : role),
};

describe("phrase du journal", () => {
  it("auteur inconnu, élément sans numéro, code inconnu : rien n'est masqué", () => {
    const sentence = entrySentence(
      entry({
        performer: { user_id: "u-x", role: "platform_admin", device_id: null },
        action: "login",
        entity: { type: "shop", id: null, number: null },
        summary: "",
      }),
      people,
    );
    expect(sentence).toBe("Utilisateur inconnu (platform_admin) s'est connecté à la boutique");
    const odd = entrySentence(
      entry({ entity: { type: "truck", id: null, number: "CE-123" }, summary: "x" }),
      { ...people, nameOf: () => "Paul" },
    );
    expect(odd).toBe("Paul (Vendeur) a créé truck CE-123 : x");
    expect(moduleLabel("transport")).toBe("transport");
  });

  it("valeurs avant/après lisibles", () => {
    expect(changeValue(null)).toBe("(vide)");
    expect(changeValue(true)).toBe("oui");
    expect(changeValue(780000)).toBe("780000");
  });

  it("filtres : « Tous » n'envoie rien ; période incohérente refusée (fail-fast)", () => {
    expect(toQuery(NO_FILTERS)).toEqual({
      from: null,
      to: null,
      userId: null,
      action: null,
      module: null,
    });
    expect(toQuery({ ...NO_FILTERS, userId: ALL, action: "cancel" }).action).toBe("cancel");
    expect(() => toQuery({ ...NO_FILTERS, from: "2026-11-10", to: "2026-11-01" })).toThrow(
      "La date de fin doit suivre la date de début",
    );
  });
});
