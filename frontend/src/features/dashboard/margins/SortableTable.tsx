import { useState, type ReactNode } from "react";
import { SortHeader, type SortDirection } from "../../../shared/ui";
import { sortRows, type SortValue } from "./marginText";

export interface Column<T> {
  key: string;
  label: string;
  numeric?: boolean;
  value: (row: T) => SortValue;
  render: (row: T) => ReactNode;
}

interface SortState {
  key: string;
  direction: SortDirection;
}

/**
 * Tableau triable (grand écran) : un appui sur un en-tête trie par cette colonne, un second
 * inverse le sens. Montants alignés à droite, chiffres à chasse fixe.
 */
export function SortableTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  initial,
}: {
  caption: string;
  columns: readonly Column<T>[];
  rows: readonly T[];
  rowKey: (row: T) => string;
  initial: SortState;
}) {
  const [sort, setSort] = useState<SortState>(initial);
  const column = columns.find((c) => c.key === sort.key);
  if (column === undefined) throw new Error(`Colonne de tri inconnue : « ${sort.key} »`);
  const sorted = sortRows(rows, column.value, sort.direction);
  const toggle = (key: string) => {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "ascending" ? "descending" : "ascending" }
        : { key, direction: "descending" },
    );
  };
  return (
    <div className="overflow-x-auto rounded-lg bg-surface p-4 shadow-card">
      <table className="w-full border-collapse text-body">
        <caption className="pb-2 text-left text-label font-semibold text-text">{caption}</caption>
        <thead>
          <tr className="border-b border-border">
            {columns.map((c) => (
              <SortHeader
                key={c.key}
                label={c.label}
                active={c.key === sort.key}
                direction={sort.direction}
                numeric={c.numeric ?? false}
                onSort={() => {
                  toggle(c.key);
                }}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={rowKey(row)} className="border-b border-border last:border-b-0">
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={`px-2 py-2 ${c.numeric === true ? "text-right tabular-nums" : "text-left"} text-text`}
                >
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
