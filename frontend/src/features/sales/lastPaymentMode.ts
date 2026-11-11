/**
 * Dernier mode de paiement utilisé, présélectionné à la vente suivante (CDC § 1.3, § 6.2).
 * Simple confort propre à l'appareil : si le stockage est indisponible (navigation privée,
 * quota, accès refusé), l'écran reprend le premier mode — l'échec est signalé en console,
 * jamais avalé en silence, et il ne bloque pas la vente.
 */
const KEY_PREFIX = "gdb.sales.lastPaymentMode.";

function keyFor(shopId: string): string {
  if (shopId === "") throw new Error("lastPaymentMode : identifiant de boutique vide");
  return KEY_PREFIX + shopId;
}

export function readLastPaymentMode(shopId: string, storage?: Storage): string | null {
  const key = keyFor(shopId);
  try {
    return (storage ?? window.localStorage).getItem(key);
  } catch (error) {
    console.warn("Dernier mode de paiement illisible : premier mode présélectionné", error);
    return null;
  }
}

export function writeLastPaymentMode(shopId: string, modeId: string, storage?: Storage): void {
  const key = keyFor(shopId);
  try {
    (storage ?? window.localStorage).setItem(key, modeId);
  } catch (error) {
    console.warn("Dernier mode de paiement non mémorisé (stockage indisponible)", error);
  }
}
