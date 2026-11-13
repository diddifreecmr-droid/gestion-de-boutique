import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, Clock, Hourglass, WifiOff, XCircle } from "lucide-react";
import { requireText } from "./controlClasses";

/** Statuts de § 6.4. */
export type BadgeStatus = "credit" | "success" | "warning" | "danger" | "offline" | "upcoming";

const STATUSES: Record<BadgeStatus, { icon: LucideIcon; classes: string }> = {
  credit: { icon: Clock, classes: "bg-credit-soft text-credit-text" },
  success: { icon: CheckCircle2, classes: "bg-success-soft text-success-text" },
  warning: { icon: AlertTriangle, classes: "bg-warning-soft text-warning-text" },
  danger: { icon: XCircle, classes: "bg-danger-soft text-danger-text" },
  offline: { icon: WifiOff, classes: "border border-border-strong bg-bg text-text-muted" },
  /** « Bientôt » : module pas encore construit (console, specs § 15.1). */
  upcoming: {
    icon: Hourglass,
    classes: "border border-dashed border-border-strong bg-bg text-text-muted",
  },
};

export interface BadgeProps {
  status: BadgeStatus;
  /** Mot du statut (« Crédit », « Soldée »…) : obligatoire, la couleur ne suffit jamais (P7). */
  children: string;
}

/** Pastille de statut (§ 6.4) : 28 px, --radius-sm, toujours mot + icône. */
export function Badge({ status, children }: BadgeProps) {
  requireText("Badge", "children", children);
  const { icon: Icon, classes } = STATUSES[status];
  return (
    <span
      className={`inline-flex min-h-7 items-center gap-1 rounded-sm px-2 text-label font-semibold whitespace-nowrap no-underline ${classes}`}
    >
      <Icon aria-hidden="true" className="size-6 shrink-0" />
      <span>{children}</span>
    </span>
  );
}
