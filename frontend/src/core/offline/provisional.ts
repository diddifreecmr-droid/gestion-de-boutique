/**
 * Numéro provisoire d'une saisie hors connexion (RG-T06, specs § 6.5) :
 * `<préfixe>-HL-<4 derniers chiffres hexadécimaux du device_id>-<séquence sur 4 chiffres>`.
 * Les **derniers** chiffres : les premiers d'un UUIDv7 sont l'horodatage, communs aux appareils.
 * Même règle que le serveur (`ProvisionalDocNumber.for_device`), qui refuse tout écart.
 */
import type { DocPrefix } from "./contract";

export function deviceCode(deviceId: string): string {
  const code = deviceId.replace(/-/g, "").slice(-4).toUpperCase();
  if (!/^[0-9A-F]{4}$/.test(code)) {
    throw new Error(`Identifiant d'appareil illisible pour un numéro provisoire : « ${deviceId} »`);
  }
  return code;
}

export function provisionalNumber(prefix: DocPrefix, deviceId: string, sequence: number): string {
  if (!Number.isSafeInteger(sequence) || sequence < 1) {
    throw new Error(`Séquence provisoire invalide : ${String(sequence)}`);
  }
  return `${prefix}-HL-${deviceCode(deviceId)}-${String(sequence).padStart(4, "0")}`;
}
