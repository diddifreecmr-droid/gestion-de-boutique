import { describe, expect, it } from "vitest";
import { defaultFilters, periodProblem, toQuery } from "./saleFilters";
import { saleRole } from "./salesNav";

const TODAY = "2026-11-11";

describe("filtres de la liste des ventes", () => {
  it("du jour par défaut (aucune date : le serveur prend le jour), mois, autres dates", () => {
    const base = defaultFilters(TODAY);
    expect(toQuery(base, TODAY)).toEqual({});
    expect(toQuery({ ...base, period: "month" }, TODAY)).toEqual({
      from: "2026-11-01",
      to: TODAY,
    });
    const custom = { ...base, period: "custom" as const, from: "2026-10-01", to: "2026-10-31" };
    expect(toQuery(custom, TODAY)).toEqual({ from: "2026-10-01", to: "2026-10-31" });
    expect(periodProblem(custom)).toBeUndefined();
    expect(periodProblem({ ...custom, to: "" })).toBe("Choisissez les deux dates");
    expect(periodProblem({ ...custom, from: "2026-11-02" })).toBe(
      "La date de début est après la date de fin",
    );
  });

  it("une recherche ignore la période et la contrôle des dates", () => {
    const search = {
      ...defaultFilters(TODAY),
      period: "custom" as const,
      from: "",
      text: " V-12 ",
    };
    expect(periodProblem(search)).toBeUndefined();
    expect(toQuery(search, TODAY)).toEqual({ q: "V-12" });
  });

  it("rôles de la section", () => {
    expect(saleRole("owner")).toBe("owner");
    expect(() => saleRole("accountant")).toThrow("ne consulte pas les ventes");
  });
});
