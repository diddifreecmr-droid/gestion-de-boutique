import type { Margins } from "../../../core/gateways/reportingContract";
import { formatMoney } from "../../../shared/format";
import { bestArticles, rateText, withoutCostText } from "./marginText";

/**
 * Coûts et marges en quelques chiffres (téléphone et grand écran) : marge totale, taux, coût,
 * puis les 3 articles qui rapportent le plus. Aucun graphique ici.
 */
export function MarginGlance({ margins }: { margins: Margins }) {
  const { totals } = margins;
  const missing = withoutCostText(totals);
  const best = bestArticles(margins.articles);
  return (
    <div className="flex flex-col gap-4">
      <dl
        aria-label="Marge de la période"
        className="m-0 flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <dt className="text-body text-text-muted">Marge totale</dt>
          <dd className="m-0 text-amount font-bold tabular-nums text-text">
            {formatMoney(totals.margin)}
          </dd>
        </div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <dt className="text-body text-text-muted">Taux de marge</dt>
          <dd className="m-0 text-lead font-semibold tabular-nums text-text">{rateText(totals)}</dd>
        </div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <dt className="text-body text-text-muted">Coût des articles vendus</dt>
          <dd className="m-0 text-lead tabular-nums text-text">{formatMoney(totals.cost)}</dd>
        </div>
      </dl>
      {missing !== null && <p className="m-0 text-body text-warning-text">{missing}</p>}
      {best.length === 0 ? (
        <p className="m-0 text-body text-text-muted">Aucune vente sur la période.</p>
      ) : (
        <ol
          aria-label="Articles qui rapportent le plus"
          className="m-0 flex list-none flex-col gap-2 rounded-lg bg-surface p-4 shadow-card"
        >
          {best.map((article, rank) => (
            <li
              key={article.article_id}
              className="flex flex-wrap items-baseline justify-between gap-2"
            >
              <span className="text-body text-text">
                {String(rank + 1)}. {article.name}
              </span>
              <span className="text-body font-semibold tabular-nums text-text">
                {formatMoney(article.figures.margin)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
