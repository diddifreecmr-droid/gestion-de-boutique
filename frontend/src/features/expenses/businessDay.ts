/**
 * Jour métier lu à Douala (fuseau de `shared/format`) : « aujourd'hui », bornes de date
 * (RG-T09) et périodes de la liste. Les dates sont des chaînes ISO « AAAA-MM-JJ ».
 */
import { BUSINESS_TIME_ZONE } from "../../shared/format";

/** Recul autorisé aux rôles autres que le propriétaire (RG-T09 : 7 jours). */
export const MAX_BACKDATE_DAYS = 7;

const isoParts = new Intl.DateTimeFormat("en-CA", {
  timeZone: BUSINESS_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** Date du jour à Douala pour l'instant `now`. */
export function businessDate(now: Date): string {
  if (Number.isNaN(now.getTime())) throw new Error("businessDate : instant invalide");
  const parts = isoParts.formatToParts(now);
  const get = (type: Intl.DateTimeFormatPartTypes) => {
    const found = parts.find((part) => part.type === type);
    if (found === undefined) throw new Error(`businessDate : partie « ${type} » absente`);
    return found.value;
  };
  return `${get("year")}-${get("month")}-${get("day")}`;
}

/** `day` décalé de `delta` jours (calendrier pur, sans fuseau). */
export function addDays(day: string, delta: number): string {
  const instant = new Date(`${day}T00:00:00Z`);
  if (Number.isNaN(instant.getTime())) throw new Error(`addDays : date invalide « ${day} »`);
  instant.setUTCDate(instant.getUTCDate() + delta);
  return instant.toISOString().slice(0, 10);
}

/** Premier jour du mois de `day`. */
export function monthStart(day: string): string {
  return `${day.slice(0, 8)}01`;
}

/** Bornes de la date d'une dépense (RG-T09) : jamais dans le futur ; 7 jours sauf propriétaire. */
export function dateBounds(today: string, isOwner: boolean): { min?: string; max: string } {
  return isOwner ? { max: today } : { min: addDays(today, -MAX_BACKDATE_DAYS), max: today };
}

/** Message d'une date hors bornes, ou `undefined` si elle est acceptée. */
export function dateProblem(day: string, today: string, isOwner: boolean): string | undefined {
  if (day === "") return "La date est vide";
  const { min, max } = dateBounds(today, isOwner);
  if (day > max) return "Une date dans le futur est refusée";
  if (min !== undefined && day < min) {
    return `Impossible de remonter à plus de ${String(MAX_BACKDATE_DAYS)} jours`;
  }
  return undefined;
}
