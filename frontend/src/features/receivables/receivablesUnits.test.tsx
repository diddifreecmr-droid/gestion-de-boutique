import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError, NetworkError } from "../../core/api/errors";
import { MODES, receivable } from "../../testing/receivables";
import { plain } from "../../testing/renderSale";
import { DEFAULT_FILTERS, toQuery } from "./filters";
import { installmentBody, installmentProblems, remainingAfter } from "./installmentDraft";
import { bandLabel, daysText, reminderStatus, statementKind, statusOf } from "./labels";
import { emptyLegacy, legacyBody, legacyProblems } from "./legacyDraft";
import { InstallmentReceiptDocument } from "./receipt/InstallmentReceiptDocument";
import { OFFLINE_MESSAGE, receivableErrorMessage } from "./receivableErrors";
import { debtsOf, originText } from "./receivableRules";
import { receivableRole } from "./receivablesNav";

const apiError = (code: string, details: Record<string, unknown> = {}) =>
  new ApiError(422, code, "Refus du serveur", details);

describe("règles et libellés des créances", () => {
  it("codes inconnus de l'API : erreur explicite (fail-fast)", () => {
    expect(statusOf("written_off").label).toBe("En perte");
    expect(bandLabel("61_90")).toBe("61 à 90 jours");
    expect(reminderStatus("postponed").label).toBe("Reporté");
    expect(statementKind("opening")).toBe("Créance ancienne");
    expect(() => statusOf("lost")).toThrow("Statut de créance inconnu");
    expect(() => bandLabel("toString")).toThrow("Classe d'ancienneté inconnu");
    expect(() => statementKind("refund")).toThrow("Opération de relevé inconnu");
    expect([daysText(0), daysText(1), daysText(2)]).toEqual(["0 jour", "1 jour", "2 jours"]);
  });

  it("rôle hors propriétaire et vendeur : erreur de garde", () => {
    expect(receivableRole("seller")).toBe("seller");
    expect(() => receivableRole("accountant")).toThrow("n'accède pas aux créances");
  });

  it("messages d'erreur : codes connus, OVERPAYMENT mal formé, erreur inattendue relancée", () => {
    expect(receivableErrorMessage(new NetworkError("coupure"))).toBe(OFFLINE_MESSAGE);
    expect(receivableErrorMessage(apiError("REASON_REQUIRED"))).toBe("Le motif est obligatoire.");
    expect(receivableErrorMessage(apiError("FORBIDDEN"))).toMatch(/pas le droit/);
    expect(receivableErrorMessage(apiError("NOT_FOUND"))).toMatch(/ne vous est pas confiée/);
    expect(receivableErrorMessage(apiError("INACTIVE_REFERENCE"))).toMatch(/désactivé/);
    expect(receivableErrorMessage(apiError("DATE_OUT_OF_RANGE"))).toMatch(/autre date/);
    expect(receivableErrorMessage(apiError("STRANGE"))).toBe(
      "L'action n'a pas abouti : Refus du serveur (STRANGE).",
    );
    expect(() => receivableErrorMessage(apiError("OVERPAYMENT", { remaining: "x" }))).toThrow(
      "OVERPAYMENT invalides",
    );
    const bug = new TypeError("bug");
    expect(() => receivableErrorMessage(bug)).toThrow(bug);
  });

  it("créances payables d'un client : En cours d'abord, puis la plus ancienne", () => {
    const a = receivable({ id: "a", opened_on: "2026-05-01", status: "written_off" });
    const b = receivable({ id: "b", opened_on: "2026-09-01" });
    const c = receivable({ id: "c", opened_on: "2026-02-01" });
    const done = receivable({ id: "d", remaining: 0, status: "settled" });
    const off = receivable({ id: "e", status: "cancelled" });
    const other = receivable({ id: "f", customer: { id: "x", name: "X", phone: "1" } });
    expect(debtsOf([a, b, c, done, off, other], "cust-moussa").map((r) => r.id)).toEqual([
      "c",
      "b",
      "a",
    ]);
    expect(originText(receivable({ sale_number: null, description: null }))).toBe(
      "Créance ancienne",
    );
  });

  it("filtres par défaut : aucun paramètre", () => {
    expect(toQuery(DEFAULT_FILTERS)).toEqual({});
  });

  it("versement : contrôles et corps", () => {
    const context = { remaining: 1000, modes: MODES, today: "2026-11-11", isOwner: false };
    const draft = { amount: null, modeId: "inconnu", paidOn: "2026-11-01", reference: "" };
    expect(installmentProblems(draft, context)).toEqual({
      amount: "Le montant est vide",
      mode: "Choisissez le mode de paiement",
      date: "Impossible de remonter à plus de 7 jours",
    });
    expect(remainingAfter(1000, 1001)).toBeNull();
    expect(() => installmentBody(draft, "id")).toThrow("Versement incomplet");
  });

  it("créance ancienne : contrôles et corps (client existant)", () => {
    const draft = { ...emptyLegacy(), openedOn: "2026-12-01" };
    expect(legacyProblems(draft, "2026-11-11").date).toBe("Une date dans le futur est refusée");
    expect(() => legacyBody(draft, "id")).toThrow("sans montant");
    expect(() => legacyBody({ ...draft, amount: 5 }, "id")).toThrow("sans client");
    const customer = {
      id: "c1",
      name: "Moussa",
      phone: "+237690000001",
      kind: "company",
      city: null,
      address: null,
      id_doc_type: null,
      id_doc_number: null,
      id_doc_photo_id: null,
      credit_limit: null,
      note: null,
      created_by: "x",
      version: 1,
    };
    const body = legacyBody(
      { ...draft, amount: 5, customer: { mode: "existing", customer }, terms: " fin mars " },
      "id",
    );
    expect(body.customer).toEqual({
      id: "c1",
      name: "Moussa",
      phone: "+237690000001",
      kind: "company",
    });
    expect(body.terms).toBe("fin mars");
    const bad = {
      ...draft,
      customer: { mode: "new" as const, name: " ", phone: "12", kind: "individual" as const },
    };
    expect(legacyProblems(bad, "2026-11-11")).toMatchObject({
      name: "Le nom est vide",
      phone: "Le téléphone doit avoir 9 chiffres",
    });
    expect(() => legacyBody({ ...bad, amount: 5 }, "id")).toThrow("Téléphone invalide");
  });

  it("reçu : récupération sur perte, versement annulé, référence du mode", () => {
    render(
      <InstallmentReceiptDocument
        receipt={{
          shop_name: "Motos Garoua",
          shop_city: null,
          shop_phone: null,
          number: "R-000009",
          paid_on: "2026-11-11",
          customer_name: "Moussa",
          customer_phone: "+237690000001",
          amount: 1000,
          mode_name: "Orange Money",
          reference: "OM-1",
          nature: "recovery",
          cancelled: true,
          total_paid: 5000,
          remaining: 3000,
          settled: false,
          sale_number: null,
        }}
      />,
    );
    const text = plain(screen.getByRole("article").textContent);
    expect(text).toContain("Orange Money (OM-1)");
    expect(screen.getByText("Récupération sur perte")).toHaveClass("receipt__mention");
    expect(screen.getByText("Versement annulé")).toBeVisible();
    expect(screen.queryByText("Soldé")).toBeNull();
  });
});
