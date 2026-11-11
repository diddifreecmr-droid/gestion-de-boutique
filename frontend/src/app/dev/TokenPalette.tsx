import { useState } from "react";

/** Nom du token (sans `--color-`) et la classe Tailwind qui le rend. */
const SWATCHES: { token: string; className: string }[] = [
  { token: "bg", className: "bg-bg" },
  { token: "surface", className: "bg-surface" },
  { token: "text", className: "bg-text" },
  { token: "text-muted", className: "bg-text-muted" },
  { token: "border", className: "bg-border" },
  { token: "border-strong", className: "bg-border-strong" },
  { token: "primary", className: "bg-primary" },
  { token: "primary-hover", className: "bg-primary-hover" },
  { token: "primary-soft", className: "bg-primary-soft" },
  { token: "on-primary", className: "bg-on-primary" },
  { token: "success", className: "bg-success" },
  { token: "success-text", className: "bg-success-text" },
  { token: "success-soft", className: "bg-success-soft" },
  { token: "warning-text", className: "bg-warning-text" },
  { token: "warning-soft", className: "bg-warning-soft" },
  { token: "warning-dot", className: "bg-warning-dot" },
  { token: "danger", className: "bg-danger" },
  { token: "danger-text", className: "bg-danger-text" },
  { token: "danger-soft", className: "bg-danger-soft" },
  { token: "credit", className: "bg-credit" },
  { token: "credit-text", className: "bg-credit-text" },
  { token: "credit-soft", className: "bg-credit-soft" },
];

/** Lit la valeur réelle des variables CSS : la page n'écrit aucune couleur en dur. */
function readTokenValues(): Record<string, string> {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(
    SWATCHES.map(({ token }) => [token, style.getPropertyValue(`--color-${token}`).trim()]),
  );
}

export function TokenPalette() {
  const [values] = useState(readTokenValues);
  return (
    <section aria-labelledby="ui-palette" className="flex flex-col gap-4">
      <h2 id="ui-palette" className="m-0 text-title-sm font-semibold">
        Palette
      </h2>
      <ul className="m-0 grid list-none grid-cols-2 gap-4 p-0 sm:grid-cols-4">
        {SWATCHES.map(({ token, className }) => (
          <li key={token} className="flex flex-col gap-1">
            <span
              aria-hidden="true"
              className={`h-12 rounded-md border border-border ${className}`}
            />
            <code className="font-mono text-body">--color-{token}</code>
            <span className="text-body text-text-muted">{values[token] || "…"}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
