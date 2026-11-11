import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { WifiOff } from "lucide-react";
import { requireText } from "./controlClasses";

export interface BannerProps {
  /** Phrase d'état : « Connexion nécessaire ». */
  title: string;
  /** Précision facultative sous le titre. */
  children?: ReactNode;
  /** Icône (WifiOff par défaut ; ex. Wrench pour une maintenance annoncée). */
  icon?: LucideIcon;
  /** Action utile (ex. un Button « Réessayer »). */
  action?: ReactNode;
}

/**
 * État durable (§ 6.5) : pleine largeur sous la barre du haut, warning-soft / warning-text.
 * `role="status"` : annoncé poliment quand il apparaît, sans couper la lecture en cours.
 */
export function Banner({ title, children, icon: Icon = WifiOff, action }: BannerProps) {
  requireText("Banner", "title", title);
  return (
    <div
      role="status"
      className="flex w-full flex-wrap items-center gap-2 bg-warning-soft px-4 py-3 text-warning-text"
    >
      <Icon aria-hidden="true" className="size-6 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col">
        <p className="m-0 text-label font-semibold">{title}</p>
        {children !== undefined && <p className="m-0 text-body">{children}</p>}
      </div>
      {action}
    </div>
  );
}
