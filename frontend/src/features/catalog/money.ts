import { formatMoney } from "../../shared/format";

/** Coût absent : aucun achat encore, le serveur ne peut pas le calculer. */
export const NOT_COMPUTABLE = "non calculable";
/** Prix absent : le vendeur tape le prix à chaque vente (UC-STK-01, étape 4). */
export const NOT_SET = "non fixé";

export function moneyOr(value: number | null, missing: string): string {
  return value === null ? missing : formatMoney(value);
}
