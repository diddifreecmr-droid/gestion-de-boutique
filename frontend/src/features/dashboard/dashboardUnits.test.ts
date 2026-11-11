import { describe, expect, it } from "vitest";
import { periodParams } from "../../core/gateways/httpReporting";
import { period } from "../../testing/dashboard";
import { readChoice, readMetric } from "./dashboardNav";
import { detailRow, totalText } from "./detailRows";
import { count, laterLot } from "./homeText";
import {
  changePercent,
  figureLabel,
  kindOf,
  percentText,
  periodText,
  previousWord,
  queryKey,
  resolveChoice,
} from "./periods";

const TODAY = "2026-11-11";
const custom = (from: string, to: string) => ({ kind: "custom" as const, from, to });

describe("périodes (UC-TDB-02)", () => {
  it("période libre : mêmes refus que le serveur", () => {
    expect(resolveChoice({ kind: "week", from: "", to: "" }, TODAY)).toEqual({
      query: { period: "week" },
    });
    expect(resolveChoice(custom("", TODAY), TODAY)).toEqual({
      problem: "Choisissez la date de début",
    });
    expect(resolveChoice(custom(TODAY, ""), TODAY)).toEqual({
      problem: "Choisissez la date de fin",
    });
    expect(resolveChoice(custom("2026-11-12", TODAY), TODAY)).toEqual({
      problem: "La date de début est après la date de fin",
    });
    expect(resolveChoice(custom(TODAY, "2026-11-12"), "2026-11-11")).toEqual({
      problem: "La période ne peut pas finir après aujourd'hui",
    });
    expect(resolveChoice(custom("2025-11-10", TODAY), TODAY)).toEqual({
      problem: "Période trop longue : 366 jours au plus",
    });
    expect(resolveChoice(custom("2025-11-11", TODAY), TODAY)).toEqual({
      query: { period: "custom", from: "2025-11-11", to: TODAY },
    });
    expect(() => resolveChoice(custom("x", "y"), "z")).toThrow("Dates invalides");
  });

  it("variation arrondie au plus proche, symétrique ; null sans base", () => {
    expect(changePercent("28.57")).toBe(29);
    expect(changePercent("-12.50")).toBe(-13);
    expect(changePercent("0.00")).toBe(0);
    expect(changePercent(null)).toBeNull();
    expect(() => changePercent("12")).toThrow("Pourcentage illisible");
    expect(percentText("-3.50")).toBe("−3,50 %");
    expect(() => percentText("x")).toThrow("Pourcentage illisible");
  });

  it("mots de la comparaison et libellés", () => {
    expect(previousWord(period("today", TODAY, TODAY, 1))).toBe("hier");
    expect(previousWord(period("yesterday", TODAY, TODAY, 1))).toBe("avant-hier");
    expect(previousWord(period("custom", TODAY, TODAY, 1))).toBe("la veille");
    expect(previousWord(period("month", "2026-11-01", TODAY, 11))).toBe("la période précédente");
    expect(figureLabel("Marge", "last_month")).toBe("Marge du mois dernier");
    expect(periodText(period("month", "2026-11-01", TODAY, 11))).toBe(
      "Du 01/11/2026 au 11/11/2026",
    );
    expect(queryKey({ period: "custom", from: "a", to: "b" })).toBe("custom:a:b");
    expect(() => kindOf(period("decade", TODAY, TODAY, 1))).toThrow("Période inconnue renvoyée");
  });

  it("adresse : période et détail inconnus refusés ; paramètres d'API", () => {
    expect(readChoice(new URLSearchParams(""))).toEqual({ kind: "today", from: "", to: "" });
    expect(() => readChoice(new URLSearchParams("periode=annee"))).toThrow("Période inconnue");
    expect(readMetric(new URLSearchParams("detail=payments"))).toBe("payments");
    expect(() => readMetric(new URLSearchParams("detail=marge"))).toThrow("Détail inconnu");
    expect(periodParams({ period: "month" })).toEqual({ period: "month" });
    expect(periodParams({ period: "custom", from: "2026-11-01", to: TODAY })).toEqual({
      period: "custom",
      from: "2026-11-01",
      to: TODAY,
    });
    expect(() => periodParams({ period: "custom", from: "", to: TODAY })).toThrow(
      "Période libre incomplète",
    );
  });
});

describe("textes et lignes de détail", () => {
  it("nombres en mots, Lot 2", () => {
    expect(count(0, "vente", "ventes", "Aucune vente")).toBe("Aucune vente");
    expect(count(0, "vente", "ventes")).toBe("0 ventes");
    expect(count(1, "vente", "ventes")).toBe("1 vente");
    expect(() => count(-1, "a", "b")).toThrow("Nombre invalide");
    expect(laterLot({ available: false, lot: 2, message: "…" })).toBe("Disponible au Lot 2");
    expect(() => laterLot({ available: false, lot: 1, message: "…" })).toThrow("mal formé");
  });

  it("lignes : champ manquant ou nature inconnue refusés ; dépense annulée ; créance", () => {
    expect(() => detailRow("s", { kind: "sale", id: "v", label: "V-1" })).toThrow(
      "Ligne « sale » v sans date",
    );
    expect(() => detailRow("s", { kind: "truck", id: "t", label: "T" })).toThrow(
      "Nature de ligne inconnue",
    );
    const expense = detailRow("s", {
      kind: "expense_category",
      id: "c",
      label: "Loyer",
      amount: -5_000,
      count: -1,
    });
    expect(expense.subtitle).toBe("1 annulation");
    const receivable = detailRow("s", {
      kind: "receivable",
      id: "r 1",
      label: "Moussa",
      day: "2026-10-01",
      amount: 300_000,
    });
    expect(receivable.subtitle).toBe("Depuis le 01/10/2026");
    expect(receivable.href).toBe("/s/s/creances?vue=fiche&id=r%201");
    expect(totalText("low_stock", 2)).toBe("2 articles sous le seuil");
  });
});
