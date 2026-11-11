import type { ReactNode } from "react";
import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import { MINUS, NBSP } from "../format";
import { CARD, PRESSABLE, moneyParts } from "./cardClasses";
import { requireText } from "./controlClasses";

export interface KpiCardProps {
  /** « Ventes du jour » (text-muted). */
  label: string;
  /** Montant en FCFA (entier). */
  amount: number;
  /** Ligne libre sous le montant (« 3 ventes »). */
  detail?: ReactNode;
  /** Variation en % (entier) par rapport à la période de référence. */
  change?: number;
  /** Référence de la variation, en mots (« par rapport à hier » par défaut). */
  changeReference?: string;
  /** Toute la carte s'ouvre d'un appui (UC-TDB-04). */
  onOpen?: () => void;
}

/** Variation en mots + flèche : « +12 % par rapport à hier » (la couleur ne porte rien, P7). */
function Change({ value, reference }: { value: number; reference: string }) {
  if (!Number.isSafeInteger(value)) {
    throw new Error(`KpiCard : change doit être un entier (en %), reçu ${String(value)}`);
  }
  const Icon = value > 0 ? ArrowUp : value < 0 ? ArrowDown : ArrowRight;
  const sign = value > 0 ? "+" : value < 0 ? MINUS : "";
  return (
    <span className="flex items-center gap-1 text-body text-text-muted">
      <Icon aria-hidden="true" className="size-6 shrink-0" />
      <span>{`${sign}${String(Math.abs(value))}${NBSP}% ${reference}`}</span>
    </span>
  );
}

/** Chiffre clé du propriétaire (§ 6.3, § 7.2) : montant en --text-kpi, « FCFA » plus petit. */
export function KpiCard({
  label,
  amount,
  detail,
  change,
  changeReference = "par rapport à hier",
  onOpen,
}: KpiCardProps) {
  requireText("KpiCard", "label", label);
  const { figure, unit } = moneyParts(amount);
  const content = (
    <span className="flex flex-col gap-1">
      <span className="text-body text-text-muted">{label}</span>
      <span className="flex flex-wrap items-baseline gap-1 text-text">
        <span className="text-kpi font-bold tabular-nums">{figure}</span>
        <span className="text-title-sm font-semibold">{unit}</span>
      </span>
      {detail !== undefined && <span className="text-body text-text-muted">{detail}</span>}
      {change !== undefined && <Change value={change} reference={changeReference} />}
    </span>
  );

  if (onOpen === undefined) return <div className={CARD}>{content}</div>;
  return (
    <button type="button" onClick={onOpen} className={`${CARD} ${PRESSABLE}`}>
      {content}
    </button>
  );
}
