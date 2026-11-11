import type { Compared, PeriodOut } from "../../core/gateways/reportingContract";
import { KpiCard } from "../../shared/ui";
import { comparison } from "./homeText";

export interface KpiProps {
  label: string;
  value: Compared;
  period: PeriodOut;
  /** Ligne sous le montant (« 3 ventes »), avant la comparaison absente. */
  detail?: string;
  onOpen?: () => void;
}

/** `KpiCard` d'un indicateur comparé : « +12 % par rapport à hier » ou la raison de son absence. */
export function Kpi({ label, value, period, detail, onOpen }: KpiProps) {
  const compared = comparison(value, period);
  const lines: string[] = [];
  if (detail !== undefined) lines.push(detail);
  if ("note" in compared) lines.push(compared.note);
  return (
    <KpiCard
      label={label}
      amount={value.value}
      {...(lines.length > 0 ? { detail: lines.join(" · ") } : {})}
      {...("change" in compared
        ? { change: compared.change, changeReference: compared.reference }
        : {})}
      {...(onOpen === undefined ? {} : { onOpen })}
    />
  );
}
