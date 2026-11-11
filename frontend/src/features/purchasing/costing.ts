/**
 * Chiffrage **indicatif** d'un achat pendant la saisie (UC-ACH-01 étape 5, RG-T10, RG-X02).
 *
 * Même règle que le serveur (`backend/app/domain/purchasing/costing.py`, `money.allocate`,
 * `quantity.yards_to_meters`), recopiée pour afficher les chiffres **avant** l'envoi ; après
 * l'enregistrement, l'écran n'affiche plus que les chiffres de la réponse (le serveur reste juge).
 * Calcul en entiers exacts (BigInt, aucun flottant) :
 *
 * - total de ligne = quantité saisie x prix, arrondi au franc le plus proche, demi vers le haut ;
 * - quantité de stock : yards x 0,9144 ou pièces x longueur, arrondi au dixième, demi vers le haut ;
 * - frais : `⌊frais x total de ligne / Σ totaux⌋`, le reste à la ligne de plus forte valeur
 *   (la première en cas d'égalité) — la somme des parts vaut exactement les frais ;
 * - coût unitaire final = (total + part des frais) / quantité de stock, même arrondi au franc.
 */
import type { EntryUnit } from "../../core/gateways/purchasingContract";

/** Ligne prête à chiffrer : quantité décimale validée (« 2.5 »), prix entier en FCFA. */
export interface CostInput {
  quantity: string;
  unit: EntryUnit;
  unitPrice: number;
  stockUnit: string;
  pieceLengthM: string | null;
}

export interface CostedLine {
  total: number;
  feeShare: number;
  /** `null` : coût non calculable (frais sur des lignes toutes à 0 FCFA, refusé au serveur). */
  finalUnitCost: number | null;
}

export interface Costing {
  lines: CostedLine[];
  merchandise: number;
  fees: number;
  total: number;
}

/** Valeur décimale positive en millièmes (« 2.5 » → 2500n). */
function thousandths(value: string): bigint {
  const match = /^(\d+)(?:\.(\d{1,3}))?$/.exec(value);
  if (match === null) throw new Error(`Quantité illisible : « ${value} »`);
  const [, whole = "0", fraction = ""] = match;
  return BigInt(whole) * 1000n + BigInt(fraction.padEnd(3, "0"));
}

/** Division entière arrondie au plus proche, demi vers le haut (n ≥ 0, d > 0). */
function roundHalfUp(n: bigint, d: bigint): bigint {
  if (n < 0n || d <= 0n) throw new Error("roundHalfUp : opérandes hors domaine");
  return (2n * n + d) / (2n * d);
}

function toNumber(value: bigint): number {
  const result = Number(value);
  if (!Number.isSafeInteger(result)) throw new Error(`Montant hors limites : ${String(value)}`);
  return result;
}

/** Quantité de stock en dixièmes de l'unité de stock (RG-X02). */
export function stockTenths(line: Omit<CostInput, "unitPrice">): bigint {
  const entered = thousandths(line.quantity);
  if (line.unit === line.stockUnit) return entered / 100n;
  if (line.stockUnit !== "METER")
    throw new Error(`Unité ${line.unit} sur un article en ${line.stockUnit}`);
  if (line.unit === "YARD") return roundHalfUp(entered * 9144n, 1_000_000n);
  if (line.unit === "PIECE" && line.pieceLengthM !== null) {
    return roundHalfUp(entered * thousandths(line.pieceLengthM), 100_000n);
  }
  throw new Error(`Unité ${line.unit} incompatible avec l'article`);
}

/** Total d'une ligne : quantité saisie x prix de l'unité saisie, au franc demi vers le haut. */
export function lineTotal(quantity: string, unitPrice: number): number {
  if (!Number.isSafeInteger(unitPrice) || unitPrice < 0) throw new Error("Prix unitaire invalide");
  return toNumber(roundHalfUp(thousandths(quantity) * BigInt(unitPrice), 1000n));
}

/** Parts des frais au prorata des totaux de ligne (somme exacte, reste à la plus forte). */
export function allocateFees(totals: readonly number[], fees: number): number[] | null {
  if (fees === 0) return totals.map(() => 0);
  const sum = totals.reduce((a, b) => a + b, 0);
  if (sum === 0) return null;
  const shares = totals.map((t) => toNumber((BigInt(fees) * BigInt(t)) / BigInt(sum)));
  let heaviest = 0;
  totals.forEach((t, i) => {
    if (t > (totals[heaviest] ?? 0)) heaviest = i;
  });
  shares[heaviest] = (shares[heaviest] ?? 0) + fees - shares.reduce((a, b) => a + b, 0);
  return shares;
}

export function costPurchase(lines: readonly CostInput[], feeAmounts: readonly number[]): Costing {
  const totals = lines.map((line) => lineTotal(line.quantity, line.unitPrice));
  const fees = feeAmounts.reduce((a, b) => a + b, 0);
  const shares = allocateFees(totals, fees);
  const costed = lines.map((line, index) => {
    const total = totals[index] ?? 0;
    const feeShare = shares?.[index] ?? 0;
    const tenths = stockTenths(line);
    const finalUnitCost =
      shares === null || tenths === 0n
        ? null
        : toNumber(roundHalfUp(BigInt(total + feeShare) * 10n, tenths));
    return { total, feeShare, finalUnitCost };
  });
  const merchandise = totals.reduce((a, b) => a + b, 0);
  return { lines: costed, merchandise, fees, total: merchandise + fees };
}
