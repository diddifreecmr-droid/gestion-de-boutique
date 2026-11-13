import { describe, expect, it } from "vitest";
import { ApiError } from "../../../core/api/errors";
import { profileFromResponse } from "../../../core/profile/servedProfile";
import { servedProfile } from "../../../testing/servedProfile";
import { attributesText, lineFieldsOf, sizeChoices, SHOE_SIZES } from "../lineFields";
import { addDays, deadlineText, exchangeAccess } from "./exchangeRules";
import { EMPLOYEE_EXCHANGE_OFF, returnErrorMessage } from "./returnErrorMessage";

const SALE = { status: "valid", sold_on: "2026-11-13", seller_id: "u-e" } as const;
const OWNER = { role: "owner", userId: "u-o" } as const;
const SELLER = { role: "seller", userId: "u-e" } as const;
const RULES = { days: 7, employeeAllowed: true };

describe("délai d'échange (QC-4) : inclusif depuis la journée de la vente", () => {
  it("addDays traverse les mois et refuse un délai négatif", () => {
    expect(addDays("2026-11-13", 7)).toBe("2026-11-20");
    expect(addDays("2026-11-28", 7)).toBe("2026-12-05");
    expect(addDays("2026-11-13", 0)).toBe("2026-11-13");
    expect(() => addDays("2026-11-13", -1)).toThrow(/Délai d'échange invalide/);
    expect(() => addDays("13/11/2026", 1)).toThrow(/AAAA-MM-JJ/);
  });

  it("employé : réglage, sa vente, dans le délai ; le 21, plus de bouton", () => {
    expect(exchangeAccess(SALE, SELLER, RULES, "2026-11-20")).toEqual({
      kind: "open",
      deadline: "2026-11-20",
      late: false,
    });
    expect(deadlineText(exchangeAccess(SALE, SELLER, RULES, "2026-11-20"))).toBe(
      "Échange possible jusqu'au 20/11",
    );
    expect(exchangeAccess(SALE, SELLER, RULES, "2026-11-21")).toEqual({
      kind: "over",
      deadline: "2026-11-20",
    });
    const off = { ...RULES, employeeAllowed: false };
    expect(exchangeAccess(SALE, SELLER, off, "2026-11-14").kind).toBe("none");
    const other = { ...SALE, seller_id: "u-e2" };
    expect(exchangeAccess(other, SELLER, RULES, "2026-11-14").kind).toBe("none");
    const cancelled = { ...SALE, status: "cancelled" };
    expect(exchangeAccess(cancelled, OWNER, RULES, "2026-11-14").kind).toBe("none");
  });

  it("propriétaire : hors délai permis, signalé ; sans délai, rien d'affiché", () => {
    const late = exchangeAccess(SALE, OWNER, RULES, "2026-11-21");
    expect(late).toEqual({ kind: "open", deadline: "2026-11-20", late: true });
    expect(deadlineText(late)).toMatch(/inscrit au journal/);
    const free = exchangeAccess(SALE, OWNER, { days: null, employeeAllowed: false }, "2027-01-01");
    expect(free).toEqual({ kind: "open", deadline: null, late: false });
    expect(deadlineText(free)).toBeNull();
  });
});

describe("règles d'échange lues du profil servi (GET /profile)", () => {
  it("exposées ; absentes d'un profil gardé avant le Lot 3 : employé fermé ; type faux : erreur", () => {
    const body = servedProfile("apparel", "seller");
    const served = { ...body, exchange_days: 7, employee_exchange_allowed: true };
    expect(profileFromResponse(served, "seller").exchange).toEqual(RULES);
    const old: Partial<typeof body> = { ...body };
    delete old.exchange_days;
    delete old.employee_exchange_allowed;
    expect(profileFromResponse(old as typeof body, "seller").exchange).toEqual({
      days: null,
      employeeAllowed: false,
    });
    const wrong = { ...body, exchange_days: "7" } as unknown as typeof body;
    expect(() => profileFromResponse(wrong, "seller")).toThrow(/exchange_days invalide/);
  });
});

describe("refus du serveur dits en clair", () => {
  it("422 EXCHANGE_PERIOD_OVER et 403 réglage désactivé", () => {
    const over = new ApiError(422, "EXCHANGE_PERIOD_OVER", "x", {
      sold_on: "2026-11-13",
      exchange_days: 7,
      deadline: "2026-11-20",
    });
    expect(returnErrorMessage(over, [], "Garoua")).toBe(
      "Délai d'échange dépassé (7 jours, jusqu'au 20/11) : seul le propriétaire peut encore échanger cette vente.",
    );
    const off = new ApiError(403, "FORBIDDEN", "x", { setting: "employee_exchange_allowed" });
    expect(returnErrorMessage(off, [], "Garoua")).toBe(EMPLOYEE_EXCHANGE_OFF);
    const broken = new ApiError(422, "EXCHANGE_PERIOD_OVER", "x", {});
    expect(() => returnErrorMessage(broken, [], "Garoua")).toThrow(/details.deadline/);
  });
});

describe("champs d'une ligne selon le profil", () => {
  it("Motos : détails par unité ; Prêt-à-porter : taille et couleur ; Textile : rien", () => {
    expect(lineFieldsOf(["color", "chassis_number", "engine_number"])).toEqual({
      units: true,
      size: false,
      color: false,
    });
    expect(lineFieldsOf(["size", "color"])).toEqual({ units: false, size: true, color: true });
    expect(lineFieldsOf(["length_m"])).toEqual({ units: false, size: false, color: false });
  });

  it("pointures pour un article chaussant ; résumé « T. M · Blanc »", () => {
    expect(sizeChoices("Baskets toile")).toBe(SHOE_SIZES);
    expect(sizeChoices("Chemise lin")).toContain("XXL");
    expect(attributesText({ size: "M", color: "Blanc" })).toBe("T. M · Blanc");
    expect(attributesText({ size: " ", color: "Rouge" })).toBe("Rouge");
  });
});
