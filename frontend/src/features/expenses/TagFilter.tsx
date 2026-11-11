import { useState } from "react";
import { Tag as TagIcon, X } from "lucide-react";
import type { Tag } from "../../core/gateways/expensesContract";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { Button, SearchField } from "../../shared/ui";
import { useLoad } from "./useLoad";

export interface TagFilterProps {
  shopId: string;
  value: Tag | null;
  onChange: (tag: Tag | null) => void;
  /** Libellé du champ (« Tag » par défaut). */
  label?: string;
}

/** Filtre « Tag » : recherche dès la première lettre (`GET /tags?search=`), un tag à la fois. */
export function TagFilter({ shopId, value, onChange, label = "Tag" }: TagFilterProps) {
  const { gateway } = useExpensesDeps();
  const [search, setSearch] = useState("");
  const typed = search.trim();
  const found = useLoad(`${shopId}:${typed}`, () =>
    typed === "" ? Promise.resolve([]) : gateway.tags(shopId, typed),
  );
  if (value !== null) {
    return (
      <div className="flex flex-col gap-2">
        <span className="text-label font-semibold text-text">{label}</span>
        <Button
          variant="secondary"
          icon={X}
          aria-label={`${label} : ${value.name} — retirer`}
          onClick={() => {
            onChange(null);
          }}
        >
          {value.name}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <SearchField label={label} value={search} onChange={setSearch} />
      {found.status === "ready" && found.value.length > 0 && (
        <ul
          aria-label={`${label} — tags trouvés`}
          className="m-0 flex list-none flex-wrap gap-2 p-0"
        >
          {found.value.map((tag) => (
            <li key={tag.id}>
              <Button
                variant="secondary"
                icon={TagIcon}
                onClick={() => {
                  setSearch("");
                  onChange(tag);
                }}
              >
                {tag.name}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
