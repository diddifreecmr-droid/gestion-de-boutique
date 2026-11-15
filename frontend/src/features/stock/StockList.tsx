import { ListCard } from "../../shared/ui";
import { groupByFabric } from "../catalog/fabricGroups";
import { StockItem } from "./StockItem";
import type { StockLine } from "./stockView";

export interface StockListProps {
  lines: readonly StockLine[];
  /** Textile : lignes rangées sous leur tissu (design-system § 7.8). */
  byFabric: boolean;
  onHistory?: (articleId: string) => void;
}

const SEPARATOR = " — ";

/**
 * Tissu d'une ligne de stock : le début de « Djampar — Rouge » (la ligne de stock ne porte pas
 * `fabric` ; le serveur nomme chaque couleur « Tissu — Couleur », décision du 2026-11-15).
 */
function fabricOf(name: string): string | null {
  const at = name.lastIndexOf(SEPARATOR);
  return at <= 0 ? null : name.slice(0, at).trim();
}

function Items({ lines, onHistory }: Omit<StockListProps, "byFabric">) {
  return lines.map((line) => (
    <StockItem
      key={line.articleId}
      line={line}
      {...(onHistory === undefined
        ? {}
        : {
            onHistory: () => {
              onHistory(line.articleId);
            },
          })}
    />
  ));
}

/** Lignes de la matrice : une liste, ou un bloc par tissu puis « Autres articles ». */
export function StockList({ lines, byFabric, onHistory }: StockListProps) {
  const history = onHistory === undefined ? {} : { onHistory };
  if (!byFabric) {
    return (
      <ListCard label="Stock par article">
        <Items lines={lines} {...history} />
      </ListCard>
    );
  }
  const groups = groupByFabric(lines.map((line) => ({ fabric: fabricOf(line.name), line })));
  const loose = groups.filter((group) => group.fabric === null).flatMap((group) => group.items);
  return (
    <>
      {groups.map((group) =>
        group.fabric === null ? null : (
          <section key={group.fabric} className="flex flex-col gap-2">
            <h2 className="m-0 text-title-sm font-semibold text-text">{group.fabric}</h2>
            <ListCard label={`Stock du tissu ${group.fabric}`}>
              <Items lines={group.items.map((item) => item.line)} {...history} />
            </ListCard>
          </section>
        ),
      )}
      {loose.length > 0 && (
        <ListCard label="Autres articles">
          <Items lines={loose.map((item) => item.line)} {...history} />
        </ListCard>
      )}
    </>
  );
}
