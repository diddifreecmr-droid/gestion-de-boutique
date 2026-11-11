import { useState } from "react";
import { Pencil } from "lucide-react";
import type { StockRow } from "../../core/gateways/stockContract";
import { Button, EmptyState, ListCard, ListCardRow, SearchField } from "../../shared/ui";
import { ErrorText } from "./Notice";

/** Nombre de propositions affichées sous la recherche. */
const SHOWN = 8;

function folded(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("fr");
}

export interface ArticleChooserProps {
  articles: readonly StockRow[];
  selected: StockRow | null;
  onSelect: (article: StockRow | null) => void;
  error?: string | undefined;
}

/** Choix de l'article : recherche dès la 1re lettre dans les articles actifs du stock. */
export function ArticleChooser({ articles, selected, onSelect, error }: ArticleChooserProps) {
  const [text, setText] = useState("");
  if (selected !== null) {
    return (
      <div className="flex flex-col gap-2">
        <span className="text-label font-semibold text-text">Article</span>
        <p className="m-0 break-words text-lead text-text">{selected.display_name}</p>
        <Button
          variant="ghost"
          icon={Pencil}
          onClick={() => {
            onSelect(null);
          }}
        >
          Changer d'article
        </Button>
      </div>
    );
  }
  const typed = folded(text.trim());
  const found =
    typed === ""
      ? []
      : articles.filter((a) => folded(a.display_name).includes(typed)).slice(0, SHOWN);
  return (
    <div className="flex flex-col gap-2">
      <SearchField
        label="Article"
        hint="Tapez le nom de l'article"
        value={text}
        onChange={setText}
      />
      {error !== undefined && <ErrorText text={error} />}
      {typed !== "" && found.length === 0 && (
        <EmptyState message={`Aucun article ne correspond à « ${text.trim()} ».`} />
      )}
      {found.length > 0 && (
        <ListCard label="Articles proposés">
          {found.map((article) => (
            <ListCardRow
              key={article.article_id}
              title={article.display_name}
              onOpen={() => {
                onSelect(article);
              }}
            />
          ))}
        </ListCard>
      )}
    </div>
  );
}
