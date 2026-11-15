import { useId, type ReactNode } from "react";
import type { Margins } from "../../../core/gateways/reportingContract";
import { articleColumns, dayColumns, fabricColumns } from "./marginColumns";
import { MarginChart } from "./MarginChart";
import { SortableTable } from "./SortableTable";

/** Jours montrés dans l'historique et le graphique : les derniers de la période. */
export const HISTORY_DAYS = 14;

function Part({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h3 id={id} className="m-0 text-lead font-semibold text-text">
        {title}
      </h3>
      {children}
    </section>
  );
}

/**
 * Coûts et marges sur grand écran (≥ 1024 px, chargé à la demande) : tableaux triables par
 * article et par tissu (au mètre et au rouleau en Textile), historique des derniers jours, et,
 * à part, le graphique des ventes et de la marge par jour.
 */
export default function MarginsWide({ margins }: { margins: Margins }) {
  const textile =
    margins.fabrics.length > 0 || margins.articles.some((a) => a.stock_unit === "METER");
  const recent = margins.days.slice(-HISTORY_DAYS);
  return (
    <div className="flex flex-col gap-6">
      <Part title="Tableaux">
        {margins.articles.length > 0 && (
          <SortableTable
            caption="Par article"
            columns={articleColumns(textile)}
            rows={margins.articles}
            rowKey={(a) => a.article_id}
            initial={{ key: "margin", direction: "descending" }}
          />
        )}
        {margins.fabrics.length > 0 && (
          <SortableTable
            caption="Par tissu (toutes couleurs)"
            columns={fabricColumns()}
            rows={margins.fabrics}
            rowKey={(f) => f.fabric}
            initial={{ key: "margin", direction: "descending" }}
          />
        )}
        <SortableTable
          caption="Historique des derniers jours"
          columns={dayColumns()}
          rows={recent}
          rowKey={(d) => d.day}
          initial={{ key: "day", direction: "descending" }}
        />
      </Part>
      {recent.length > 1 && (
        <Part title="Graphiques">
          <MarginChart days={recent} />
        </Part>
      )}
    </div>
  );
}
