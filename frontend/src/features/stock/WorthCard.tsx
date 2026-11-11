import { KpiCard } from "../../shared/ui";
import { formatMoney } from "../../shared/format";
import { NOT_COMPUTABLE } from "../catalog/money";
import { Facts } from "./Facts";
import { missingText, worthText, type Worth } from "./valuation";

/** Chiffre clé de la valeur : le montant, ou « non calculable » avec la part connue (RG-T15). */
export function WorthCard({ label, worth }: { label: string; worth: Worth }) {
  if (worth.amount !== null) {
    return (
      <KpiCard
        label={label}
        amount={worth.amount}
        {...(worth.missing > 0 ? { detail: missingText(worth.missing) } : {})}
      />
    );
  }
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-surface p-4 shadow-card">
      <span className="text-body text-text-muted">{label}</span>
      <span className="text-amount font-bold text-text">{NOT_COMPUTABLE}</span>
      <span className="text-body text-text">{`Part connue : ${formatMoney(worth.known)}`}</span>
      <span className="text-body text-text-muted">{missingText(worth.missing)}</span>
    </div>
  );
}

export function WorthFacts({ rows }: { rows: readonly { label: string; worth: Worth }[] }) {
  return <Facts facts={rows.map((row) => ({ label: row.label, value: worthText(row.worth) }))} />;
}
