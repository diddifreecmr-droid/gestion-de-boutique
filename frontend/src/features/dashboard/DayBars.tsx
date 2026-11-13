import type { Series } from "../../core/gateways/reportingContract";
import { formatDate, formatMoney } from "../../shared/format";
import { barWidth } from "../expenses/barWidth";
import { Section } from "./Section";

/** Largeur d'une barre ; une valeur négative (marge) n'a pas de barre, son montant suffit. */
function width(value: number, max: number): string {
  return value <= 0 || max <= 0 ? "w-0" : barWidth(value, max);
}

function Bar({ label, value, max, tone }: Readonly<BarProps>) {
  const negative = value < 0;
  return (
    <div className="flex flex-col gap-1">
      <span className="flex flex-wrap items-baseline justify-between gap-2 text-body">
        <span className="text-text-muted">{label}</span>
        <span className={`tabular-nums ${negative ? "text-danger-text" : "text-text"}`}>
          {formatMoney(value)}
        </span>
      </span>
      <span aria-hidden="true" className="block h-3 w-full rounded-sm bg-bg">
        <span className={`block h-3 rounded-sm ${tone} ${width(value, max)}`} />
      </span>
    </div>
  );
}

interface BarProps {
  label: string;
  value: number;
  max: number;
  tone: "bg-primary" | "bg-text-muted";
}

function Totals({ series }: { series: Series }) {
  const rows = [
    ["Total des ventes", series.total_sales],
    ["Ventes en moyenne par jour", series.average_sales],
    ["Total de la marge", series.total_margin],
    ["Marge en moyenne par jour", series.average_margin],
  ] as const;
  return (
    <dl className="m-0 flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
      {rows.map(([label, amount]) => (
        <div key={label} className="flex flex-wrap items-baseline justify-between gap-2">
          <dt className="text-body text-text-muted">{label}</dt>
          <dd className="m-0 text-lead font-semibold tabular-nums text-text">
            {formatMoney(amount)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * UC-TDB-02 : ventes et marge jour par jour, en barres composées de tokens (sans bibliothèque).
 * Chaque barre suit son libellé et son montant écrits : la liste se lit sans le dessin, et la
 * barre (décorative) ne porte rien seule. Même échelle pour les ventes et la marge.
 */
export function DayBars({ series }: { series: Series }) {
  const { points } = series;
  if (points.length < 2) throw new Error(`Série jour par jour de ${String(points.length)} jour`);
  const max = Math.max(0, ...points.flatMap((point) => [point.sales, point.margin]));
  return (
    <Section
      title="Jour par jour"
      summary={`Ventes ${formatMoney(series.total_sales)} · Marge ${formatMoney(series.total_margin)}`}
    >
      <Totals series={series} />
      <ul
        aria-label="Ventes et marge par jour"
        className="m-0 flex list-none flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
      >
        {points.map((point) => (
          <li key={point.day} className="flex flex-col gap-2">
            <span className="text-label font-semibold text-text">{formatDate(point.day)}</span>
            <Bar label="Ventes" value={point.sales} max={max} tone="bg-primary" />
            <Bar label="Marge" value={point.margin} max={max} tone="bg-text-muted" />
          </li>
        ))}
      </ul>
    </Section>
  );
}
