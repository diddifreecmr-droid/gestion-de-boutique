/** Classes du Button (design-system.md § 6.1), construites uniquement à partir des tokens. */

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "md" | "lg";

/** Libellé affiché pendant l'envoi (design-system.md § 6.1). */
export const LOADING_LABEL = "Envoi…";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 text-label font-semibold " +
  "select-none transition-colors duration-(--duration-fast) ease-out " +
  "outline-none focus-visible:ring-2 focus-visible:ring-primary " +
  "focus-visible:ring-offset-3 focus-visible:ring-offset-surface";

/** Couleurs au repos, puis réaction à l'appui (retirée quand le bouton est indisponible). */
const VARIANTS: Record<ButtonVariant, { rest: string; press: string }> = {
  primary: {
    rest: "bg-primary text-on-primary",
    press: "hover:bg-primary-hover active:bg-primary-hover",
  },
  secondary: {
    rest: "border border-border-strong bg-surface text-primary",
    press: "hover:bg-primary-soft active:bg-primary-soft",
  },
  ghost: {
    rest: "bg-transparent text-primary",
    press: "hover:bg-primary-soft active:bg-primary-soft",
  },
  // Pas de token « danger-hover » : l'appui fonce vers danger-text (blanc dessus ≈ 8,9:1).
  danger: {
    rest: "bg-danger text-on-primary",
    press: "hover:bg-danger-text active:bg-danger-text",
  },
};

/** Hauteurs minimales = tokens --control-md (48 px) et --control-lg (56 px). */
const SIZES: Record<ButtonSize, string> = {
  md: "min-h-(--control-md)",
  lg: "min-h-(--control-lg)",
};

const UNAVAILABLE = "cursor-not-allowed opacity-50";

export function buttonClasses(
  variant: ButtonVariant,
  size: ButtonSize,
  fullWidth: boolean,
  unavailable: boolean,
): string {
  const { rest, press } = VARIANTS[variant];
  return [BASE, rest, unavailable ? UNAVAILABLE : press, SIZES[size], fullWidth ? "w-full" : ""]
    .filter((c) => c !== "")
    .join(" ");
}
