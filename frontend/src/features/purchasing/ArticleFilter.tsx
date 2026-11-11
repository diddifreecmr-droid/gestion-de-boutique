import { useState } from "react";
import { X } from "lucide-react";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { Button, ListCard, ListCardRow, SearchField } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { ARTICLE_RESULTS } from "./ArticleSearch";

export interface ArticleFilterProps {
  shopId: string;
  value: { id: string; name: string } | null;
  onChange: (article: { id: string; name: string } | null) => void;
}

/** Filtre « Article » de la liste (UC-ACH-05) : recherche dans le catalogue, archivés compris. */
export function ArticleFilter({ shopId, value, onChange }: ArticleFilterProps) {
  const { catalog } = usePurchasingDeps();
  const [text, setText] = useState("");
  const typed = text.trim();
  const found = useLoad(`${shopId}:${typed}`, () =>
    typed === ""
      ? Promise.resolve(null)
      : catalog.listArticles(shopId, {
          text: typed,
          status: "all",
          cursor: null,
          limit: ARTICLE_RESULTS,
        }),
  );
  if (value !== null) {
    return (
      <div className="flex flex-col gap-2">
        <span className="text-label font-semibold text-text">Article</span>
        <p className="m-0 break-words text-lead text-text">{value.name}</p>
        <Button
          variant="ghost"
          icon={X}
          onClick={() => {
            onChange(null);
            setText("");
          }}
        >
          Tous les articles
        </Button>
      </div>
    );
  }
  const items = found.status === "ready" ? (found.value?.items ?? []) : [];
  return (
    <div className="flex flex-col gap-2">
      <SearchField label="Article" value={text} onChange={setText} />
      {items.length > 0 && (
        <ListCard label="Articles à filtrer">
          {items.map((article) => (
            <ListCardRow
              key={article.id}
              title={article.display_name}
              onOpen={() => {
                onChange({ id: article.id, name: article.display_name });
              }}
            />
          ))}
        </ListCard>
      )}
    </div>
  );
}
