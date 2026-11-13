import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { CheckCircle2, Info, XCircle } from "lucide-react";

export type CountTone = "success" | "danger" | "muted";

const TONES: Record<CountTone, { icon: LucideIcon; classes: string }> = {
  success: { icon: CheckCircle2, classes: "bg-success-soft text-success-text" },
  danger: { icon: XCircle, classes: "bg-danger-soft text-danger-text" },
  muted: { icon: Info, classes: "bg-surface text-text-muted" },
};

/** Une ligne du bilan d'un aperçu ou d'un rapport (design-system § 7.7) : icône + phrase. */
export function CountLine({ tone, children }: { tone: CountTone; children: string }) {
  const { icon: Icon, classes } = TONES[tone];
  return (
    <li className={`flex items-start gap-2 rounded-md px-4 py-3 text-body ${classes}`}>
      <Icon aria-hidden="true" className="size-6 shrink-0" />
      <span>{children}</span>
    </li>
  );
}

/** Liste des lignes de bilan, nommée pour les lecteurs d'écran. */
export function CountList({ label, children }: { label: string; children: ReactNode }) {
  return (
    <ul aria-label={label} className="m-0 flex list-none flex-col gap-2 p-0">
      {children}
    </ul>
  );
}
