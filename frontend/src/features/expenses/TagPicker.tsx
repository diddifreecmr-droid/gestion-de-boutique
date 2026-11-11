import { useState } from "react";
import { Plus, Tag as TagIcon, X } from "lucide-react";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { Button, SearchField } from "../../shared/ui";
import { useLoad } from "./useLoad";

/** Au plus 10 tags par dépense (règle du serveur, `MAX_TAGS`). */
export const MAX_TAGS = 10;

export interface TagPickerProps {
  shopId: string;
  value: readonly string[];
  onChange: (tags: string[]) => void;
}

const key = (name: string) => name.trim().toLocaleLowerCase("fr");

/**
 * Tags (UC-DEP-02) : choisis parmi les suggestions (`GET /tags?search=`, dès la première
 * lettre) ou créés à la volée en tapant un mot nouveau ; le serveur crée le tag à l'envoi.
 */
export function TagPicker({ shopId, value, onChange }: TagPickerProps) {
  const { gateway } = useExpensesDeps();
  const [search, setSearch] = useState("");
  const typed = search.trim();
  const found = useLoad(`${shopId}:${typed}`, () =>
    typed === "" ? Promise.resolve([]) : gateway.tags(shopId, typed),
  );
  const chosen = new Set(value.map(key));
  const full = value.length >= MAX_TAGS;

  const add = (name: string) => {
    if (full || chosen.has(key(name))) return;
    onChange([...value, name.trim()]);
    setSearch("");
  };

  const suggestions =
    found.status === "ready" ? found.value.filter((tag) => !chosen.has(key(tag.name))) : [];
  const known = found.status === "ready" && found.value.some((tag) => key(tag.name) === key(typed));
  const canCreate = typed !== "" && !known && !chosen.has(key(typed)) && !full;

  return (
    <div className="flex flex-col gap-2">
      <SearchField
        label="Tags"
        hint={
          full ? `${String(MAX_TAGS)} tags au plus` : "Choisissez un tag ou tapez-en un nouveau"
        }
        value={search}
        onChange={setSearch}
      />
      {found.status === "offline" && (
        <p className="m-0 text-body text-text-muted">Suggestions indisponibles hors connexion.</p>
      )}
      {(suggestions.length > 0 || canCreate) && (
        <ul aria-label="Tags proposés" className="m-0 flex list-none flex-wrap gap-2 p-0">
          {suggestions.map((tag) => (
            <li key={tag.id}>
              <Button
                variant="secondary"
                icon={TagIcon}
                onClick={() => {
                  add(tag.name);
                }}
              >
                {tag.name}
              </Button>
            </li>
          ))}
          {canCreate && (
            <li>
              <Button
                variant="secondary"
                icon={Plus}
                onClick={() => {
                  add(typed);
                }}
              >
                {`Créer le tag « ${typed} »`}
              </Button>
            </li>
          )}
        </ul>
      )}
      {value.length > 0 && (
        <ul aria-label="Tags choisis" className="m-0 flex list-none flex-wrap gap-2 p-0">
          {value.map((name) => (
            <li key={key(name)}>
              <Button
                variant="ghost"
                icon={X}
                aria-label={`Retirer le tag ${name}`}
                onClick={() => {
                  onChange(value.filter((other) => key(other) !== key(name)));
                }}
              >
                {name}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
