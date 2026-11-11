import { describe, expect, it } from "vitest";
import { ApiError, NetworkError } from "../../core/api/errors";
import type { ProfileFieldResponse } from "../../core/gateways/catalogAdminContract";
import { profileBody } from "../../testing/catalog";
import { loadFailureMessage, OFFLINE_SAVE, submitFailure } from "./catalogErrors";
import { thresholdValue } from "./extraValues";
import { changedValues, checkDraft, draftOf, fieldKind, fieldValues } from "./fieldValues";

const spec = (kind: string, extra: Partial<ProfileFieldResponse> = {}): ProfileFieldResponse => ({
  code: kind,
  label: kind,
  kind,
  required: false,
  unique: false,
  choices: [],
  ...extra,
});

describe("champs du profil", () => {
  const fields = [
    ...profileBody("owner").article_fields,
    spec("decimal"),
    spec("boolean"),
    spec("choice", { choices: ["Route", "Tricycle"] }),
  ];

  it("convertit la saisie vers les valeurs de l'API", () => {
    const draft = {
      brand: " Haojue ",
      model: "HJ125-8",
      engine_cc: "125",
      category: "",
      decimal: "2,5",
      boolean: "false",
      choice: "Route",
    };
    expect(checkDraft(fields, draft)).toEqual({});
    expect(fieldValues(fields, draft)).toEqual({
      brand: "Haojue",
      model: "HJ125-8",
      engine_cc: 125,
      decimal: "2.5",
      boolean: false,
      choice: "Route",
    });
  });

  it("refuse obligatoire vide, entier, décimal et choix invalides", () => {
    const draft = { brand: "", model: "x", engine_cc: "0", decimal: "2.555", choice: "Avion" };
    expect(checkDraft(fields, draft)).toEqual({
      brand: "Marque : champ obligatoire",
      engine_cc: "Cylindrée (cm³) : nombre entier attendu (ex. 125)",
      decimal: "decimal : nombre attendu (ex. 2,5)",
      choice: "choice : choix inconnu",
    });
  });

  it("modification : seuls les champs changés, un champ vidé part à null", () => {
    const before = draftOf(fields, { brand: "Haojue", engine_cc: 125, boolean: true });
    expect(before).toMatchObject({ brand: "Haojue", engine_cc: "125", boolean: "true", model: "" });
    const after = { ...before, engine_cc: "", category: "Route" };
    expect(changedValues(fields, before, after)).toEqual({ engine_cc: null, category: "Route" });
  });

  it("type inconnu : erreur explicite ; seuil au point décimal", () => {
    expect(() => fieldKind(spec("date"))).toThrow("Type de champ inconnu « date »");
    expect(thresholdValue(" 2,5 ")).toBe("2.5");
    expect(thresholdValue("")).toBeNull();
  });
});

describe("refus traduits", () => {
  it("réseau, détails mal formés, erreur imprévue relancée", () => {
    expect(submitFailure(new NetworkError("x"))).toEqual({ kind: "message", text: OFFLINE_SAVE });
    expect(() => submitFailure(new ApiError(409, "DUPLICATE", "x", {}))).toThrow("existing_id");
    expect(() =>
      submitFailure(new ApiError(422, "MIN_PRICE_ABOVE_BASE", "x", { min_price: "1" })),
    ).toThrow("min_price");
    const bug = new TypeError("bug");
    expect(() => submitFailure(bug)).toThrow(bug);
  });

  it("droits et messages du serveur", () => {
    expect(submitFailure(new ApiError(403, "FORBIDDEN", "x"))).toEqual({
      kind: "message",
      text: "Vous n'avez pas le droit de faire cette action.",
    });
    expect(submitFailure(new ApiError(422, "VALIDATION_ERROR", "Champ obligatoire"))).toEqual({
      kind: "message",
      text: "Champ obligatoire",
    });
    expect(loadFailureMessage(new ApiError(403, "FORBIDDEN", "x"))).toMatch("pas le droit");
    expect(loadFailureMessage(new ApiError(400, "OTHER", "Autre"))).toBe("Autre");
  });
});
