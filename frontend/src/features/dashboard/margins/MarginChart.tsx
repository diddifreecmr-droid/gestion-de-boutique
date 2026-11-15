import type { DayMargin } from "../../../core/gateways/reportingContract";
import { formatDate, formatMoney } from "../../../shared/format";

const BAR = 10;
const GAP = 4;
const STEP = BAR * 2 + GAP * 3;
const HEIGHT = 120;

/** Hauteur d'une barre ; une marge négative n'a pas de barre (son montant est dans le tableau). */
function height(value: number, max: number): number {
  return value <= 0 || max <= 0 ? 0 : Math.max(1, Math.round((value / max) * HEIGHT));
}

/**
 * Graphique « Ventes et marge par jour » (grand écran seulement) : SVG maison, sans
 * bibliothèque, couleurs des tokens (`fill-primary`, `fill-text-muted`). Décoratif pour un
 * lecteur d'écran, qui lit le même contenu dans le tableau « Historique » : le graphique porte
 * un résumé (`role="img"`).
 */
export function MarginChart({ days }: { days: readonly DayMargin[] }) {
  const max = Math.max(0, ...days.flatMap((d) => [d.revenue, d.margin]));
  const total = days.reduce((sum, d) => sum + d.margin, 0);
  const first = days[0];
  const last = days[days.length - 1];
  if (first === undefined || last === undefined) throw new Error("Graphique sans jour");
  const label = `Ventes et marge par jour, du ${formatDate(first.day)} au ${formatDate(last.day)} ; marge totale ${formatMoney(total)}`;
  return (
    <figure className="m-0 flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
      <svg
        role="img"
        aria-label={label}
        viewBox={`0 0 ${String(days.length * STEP)} ${String(HEIGHT)}`}
        preserveAspectRatio="none"
        className="h-48 w-full"
      >
        {days.map((d, i) => {
          const x = i * STEP + GAP;
          const sales = height(d.revenue, max);
          const margin = height(d.margin, max);
          return (
            <g key={d.day}>
              <rect x={x} y={HEIGHT - sales} width={BAR} height={sales} className="fill-primary" />
              <rect
                x={x + BAR + GAP}
                y={HEIGHT - margin}
                width={BAR}
                height={margin}
                className="fill-text-muted"
              />
            </g>
          );
        })}
      </svg>
      <figcaption className="flex flex-wrap gap-4 text-body text-text-muted">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="size-3 rounded-sm bg-primary" />
          Ventes
        </span>
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="size-3 rounded-sm bg-text-muted" />
          Marge
        </span>
      </figcaption>
    </figure>
  );
}
