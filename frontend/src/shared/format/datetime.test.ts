import { describe, expect, it } from "vitest";
import { BUSINESS_TIME_ZONE, FormatError, formatDate, formatTime } from "./index";

const N = " ";

describe("formatDate", () => {
  it("formate en JJ/MM/AAAA", () => {
    expect(formatDate("2026-11-10T09:15:00Z")).toBe("10/11/2026");
  });

  it("accepte un objet Date", () => {
    expect(formatDate(new Date(Date.UTC(2026, 0, 5, 12, 0)))).toBe("05/01/2026");
  });

  it("lit l'instant à Douala (UTC+1) : 23 h 30 UTC est déjà le lendemain", () => {
    expect(BUSINESS_TIME_ZONE).toBe("Africa/Douala");
    expect(formatDate("2026-11-10T23:30:00Z")).toBe("11/11/2026");
    expect(formatDate("2026-12-31T23:00:00Z")).toBe("01/01/2027");
  });

  it("respecte un décalage explicite", () => {
    expect(formatDate("2026-11-11T00:30:00+01:00")).toBe("11/11/2026");
  });

  it("affiche un jour métier (date seule) sans conversion de fuseau", () => {
    expect(formatDate("2026-11-10")).toBe("10/11/2026");
    expect(formatDate("2028-02-29")).toBe("29/02/2028");
  });

  it.each(["2026-02-30", "2026-13-01", "10/11/2026", "2026-11-10T10:00:00", "", "demain"])(
    "lève une FormatError pour « %s »",
    (value) => {
      expect(() => formatDate(value)).toThrow(FormatError);
    },
  );

  it("lève une FormatError pour une Date invalide", () => {
    expect(() => formatDate(new Date(Number.NaN))).toThrow(FormatError);
    expect(() => formatDate("2026-13-45T10:00:00Z")).toThrow("Date invalide");
  });
});

describe("formatTime", () => {
  it("formate en « HH h MM » avec espaces insécables", () => {
    expect(formatTime("2026-11-10T13:32:00Z")).toBe(`14${N}h${N}32`);
  });

  it("affiche minuit à Douala comme 00 h 00 (jamais 24 h)", () => {
    expect(formatTime("2026-11-10T23:00:00Z")).toBe(`00${N}h${N}00`);
  });

  it("complète par des zéros", () => {
    expect(formatTime("2026-11-10T08:05:00Z")).toBe(`09${N}h${N}05`);
  });

  it("donne 23 h 59 juste avant le changement de jour à Douala", () => {
    expect(formatTime("2026-11-10T22:59:59.999Z")).toBe(`23${N}h${N}59`);
    expect(formatDate("2026-11-10T22:59:59.999Z")).toBe("10/11/2026");
  });

  it.each(["2026-11-10", "14:32", "2026-11-10T13:32:00"])(
    "refuse « %s » (pas un instant avec fuseau)",
    (value) => {
      expect(() => formatTime(value)).toThrow(FormatError);
    },
  );
});
