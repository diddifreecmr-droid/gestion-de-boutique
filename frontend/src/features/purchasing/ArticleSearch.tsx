import { useState } from "react";
import { CirclePlus } from "lucide-react";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { Button, EmptyState, ListCard, ListCardRow, SearchField, Skeleton } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { useLoad } from "../expenses/useLoad";
import { ArticleCreatePanel } from "./ArticleCreatePanel";
import { draftArticle, type DraftArticle } from "./draft";
import type { PurchaseRole } from "./purchasingNav";

/** Nombre d'articles proposés sous la recherche. */
export const ARTICLE_RESULTS = 8;

export interface ArticleSearchProps {
  shopId: string;
  role: PurchaseRole;
  onSelect: (article: DraftArticle) => void;
  error?: string | undefined;
}

/**
 * Article d'une ligne : recherche dans le catalogue dès la 1re lettre (articles actifs), et
 * « Créer l'article » sans quitter la saisie (UC-ACH-01, cas « article introuvable ») : le
 * formulaire du catalogue s'ouvre dans le flux, l'article créé est aussitôt choisi.
 */
export function ArticleSearch({ shopId, role, onSelect, error }: ArticleSearchProps) {
  const { catalog } = usePurchasingDeps();
  const [text, setText] = useState("");
  const [creating, setCreating] = useState(false);
  const typed = text.trim();
  const found = useLoad(`${shopId}:${typed}`, () =>
    typed === ""
      ? Promise.resolve(null)
      : catalog.listArticles(shopId, {
          text: typed,
          status: "active",
          cursor: null,
          limit: ARTICLE_RESULTS,
        }),
  );

  if (creating) {
    return (
      <ArticleCreatePanel
        shopId={shopId}
        role={role}
        onCreated={(article) => {
          onSelect(draftArticle(article));
        }}
        onClose={() => {
          setCreating(false);
        }}
      />
    );
  }

  const items = found.status === "ready" ? (found.value?.items ?? []) : [];
  return (
    <div className="flex flex-col gap-2">
      <SearchField
        label="Article"
        hint="Tapez le nom de l'article"
        value={text}
        onChange={setText}
      />
      {error !== undefined && <FormMessage text={error} />}
      {typed !== "" && found.status === "loading" && (
        <Skeleton lines={2} label="Recherche des articles…" />
      )}
      {found.status === "offline" && (
        <FormMessage text="Connexion nécessaire pour chercher un article." />
      )}
      {found.status === "ready" && found.value !== null && items.length === 0 && (
        <EmptyState message={`Aucun article ne correspond à « ${typed} ».`} />
      )}
      {items.length > 0 && (
        <ListCard label="Articles proposés">
          {items.map((article) => (
            <ListCardRow
              key={article.id}
              title={article.display_name}
              onOpen={() => {
                onSelect(draftArticle(article));
              }}
            />
          ))}
        </ListCard>
      )}
      {found.status === "ready" && found.value !== null && (
        <Button
          variant="secondary"
          icon={CirclePlus}
          onClick={() => {
            setCreating(true);
          }}
        >
          Créer l'article
        </Button>
      )}
    </div>
  );
}
