import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { requireText } from "./controlClasses";

export interface EmptyStateProps {
  /** Une phrase : « Aucune vente aujourd'hui ». */
  message: string;
  /** L'action utile : un Button « Nouvelle vente ». */
  action?: ReactNode;
  /** Icône d'accompagnement facultative (décorative, le message porte le sens). */
  icon?: LucideIcon;
}

/** Liste vide (§ 6.5) : une phrase + l'action utile, rien d'autre (P4). */
export function EmptyState({ message, action, icon: Icon }: EmptyStateProps) {
  requireText("EmptyState", "message", message);
  return (
    <div className="flex flex-col items-center gap-4 rounded-lg bg-surface p-6 text-center">
      {Icon !== undefined && <Icon aria-hidden="true" className="size-8 text-text-muted" />}
      <p className="m-0 text-lead text-text">{message}</p>
      {action}
    </div>
  );
}
