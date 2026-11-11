/**
 * Valeur de l'en-tête `X-Captured-At` (specs § 6.1) : l'heure de l'**appareil** au moment de
 * la saisie, en ISO 8601 avec le décalage du fuseau local (« 2026-11-11T10:05:00.000+01:00 »).
 * Le serveur la garde à côté de son heure de réception ; elle ne décide de rien.
 */
const pad = (value: number, size = 2) => String(value).padStart(size, "0");

export function capturedAtHeader(at: Date): string {
  if (Number.isNaN(at.getTime())) throw new Error("X-Captured-At : instant invalide");
  const offset = -at.getTimezoneOffset();
  const sign = offset >= 0 ? "+" : "-";
  const zone = `${sign}${pad(Math.floor(Math.abs(offset) / 60))}:${pad(Math.abs(offset) % 60)}`;
  const day = `${String(at.getFullYear())}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
  const time = `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;
  return `${day}T${time}.${pad(at.getMilliseconds(), 3)}${zone}`;
}
