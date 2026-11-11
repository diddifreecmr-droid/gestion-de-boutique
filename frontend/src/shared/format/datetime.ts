import { NBSP } from "./characters";
import { FormatError } from "./errors";

/** Fuseau métier : toutes les boutiques sont au Cameroun (specs.md, BusinessDay). */
export const BUSINESS_TIME_ZONE = "Africa/Douala";

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;
/** Une date-heure doit porter son fuseau (Z ou ±hh:mm), sinon elle est ambiguë. */
const DATE_TIME_WITH_ZONE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/;

const dateParts = new Intl.DateTimeFormat("fr-FR", {
  timeZone: BUSINESS_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});
const timeParts = new Intl.DateTimeFormat("fr-FR", {
  timeZone: BUSINESS_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function toInstant(value: Date | string): Date {
  if (typeof value === "string" && !DATE_TIME_WITH_ZONE.test(value)) {
    throw new FormatError(`Date-heure sans fuseau ou invalide : « ${value} »`);
  }
  const instant = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(instant.getTime())) {
    throw new FormatError(`Date invalide : « ${String(value)} »`);
  }
  return instant;
}

function part(parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes): string {
  const found = parts.find((p) => p.type === type);
  if (found === undefined) {
    throw new FormatError(`Partie « ${type} » absente du format de date`);
  }
  return found.value;
}

/**
 * Date au format JJ/MM/AAAA, lue à Douala : « 10/11/2026 ».
 * Une date seule « 2026-11-10 » (jour métier venu de l'API) est affichée telle quelle,
 * sans conversion de fuseau.
 */
export function formatDate(value: Date | string): string {
  if (typeof value === "string") {
    const match = DATE_ONLY.exec(value);
    if (match !== null) {
      const [, year = "", month = "", day = ""] = match;
      const check = new Date(`${value}T00:00:00Z`);
      if (Number.isNaN(check.getTime()) || check.toISOString().slice(0, 10) !== value) {
        throw new FormatError(`Date invalide : « ${value} »`);
      }
      return `${day}/${month}/${year}`;
    }
  }
  const parts = dateParts.formatToParts(toInstant(value));
  return `${part(parts, "day")}/${part(parts, "month")}/${part(parts, "year")}`;
}

/** Heure au format « 14 h 32 » (espaces insécables), lue à Douala, de 00 h 00 à 23 h 59. */
export function formatTime(value: Date | string): string {
  const parts = timeParts.formatToParts(toInstant(value));
  return `${part(parts, "hour")}${NBSP}h${NBSP}${part(parts, "minute")}`;
}
