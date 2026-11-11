import { useId, type ButtonHTMLAttributes, type MouseEvent, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { buttonClasses, LOADING_LABEL, type ButtonSize, type ButtonVariant } from "./buttonClasses";

export type { ButtonSize, ButtonVariant };

type NativeProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "className" | "style" | "disabled" | "children"
>;

export interface ButtonProps extends NativeProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Icône Lucide affichée à gauche du libellé (jamais seule, P5). */
  icon?: LucideIcon;
  /** Pleine largeur (action principale sur téléphone). */
  fullWidth?: boolean;
  /**
   * Raison pour laquelle le bouton est indisponible. Sa seule présence désactive le
   * bouton : un bouton grisé sans explication est impossible par construction.
   */
  disabledReason?: string;
  /** Envoi en cours : libellé « Envoi… », appuis ignorés (double appui bloqué). */
  loading?: boolean;
  children: ReactNode;
}

/**
 * Bouton du design system (§ 6.1). Indisponible = `aria-disabled` : il reste focalisable,
 * pour que la raison (reliée par aria-describedby) soit lue, et les clics sont bloqués.
 */
export function Button({
  variant = "primary",
  size = "md",
  icon: Icon,
  fullWidth = false,
  disabledReason,
  loading = false,
  type = "button",
  onClick,
  children,
  ...rest
}: ButtonProps) {
  const reasonId = useId();
  if (disabledReason?.trim() === "") {
    throw new Error("Button : disabledReason ne peut pas être vide (une raison doit être lue)");
  }
  const disabled = disabledReason !== undefined;
  const unavailable = disabled || loading;
  const describedBy = [rest["aria-describedby"], disabled ? reasonId : undefined]
    .filter((id) => id !== undefined)
    .join(" ");

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    if (unavailable) {
      event.preventDefault();
      return;
    }
    onClick?.(event);
  };

  const button = (
    <button
      {...rest}
      type={type}
      className={buttonClasses(variant, size, fullWidth, unavailable)}
      aria-disabled={unavailable || undefined}
      aria-busy={loading || undefined}
      aria-describedby={describedBy === "" ? undefined : describedBy}
      onClick={handleClick}
    >
      {Icon !== undefined && <Icon aria-hidden="true" className="size-6 shrink-0" />}
      <span>{loading ? LOADING_LABEL : children}</span>
    </button>
  );

  if (!disabled) return button;
  return (
    <div className={fullWidth ? "flex w-full flex-col gap-1" : "inline-flex flex-col gap-1"}>
      {button}
      <p id={reasonId} className="m-0 text-body text-text-muted">
        {disabledReason}
      </p>
    </div>
  );
}
