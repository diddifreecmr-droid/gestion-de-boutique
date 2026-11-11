import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { ListCard, ListCardRow } from "../../shared/ui";
import { ArchivedBadge } from "./ArchivedBadge";
import { articleView, costsOf, pricesOf, type ArticleView } from "./articleView";
import type { CatalogRole } from "./catalogRights";
import { moneyOr, NOT_COMPUTABLE, NOT_SET } from "./money";

/** Sous-ligne selon le rôle : prix de base (propriétaire) ou CMP (comptable, sans prix). */
function subtitle(view: ArticleView): string {
  const prices = pricesOf(view);
  if (prices !== null) return `Prix de base : ${moneyOr(prices.basePrice, NOT_SET)}`;
  const costs = costsOf(view);
  if (costs === null) throw new Error("Vue d'article sans prix ni coût");
  return `Coût moyen (CMP) : ${moneyOr(costs.wac, NOT_COMPUTABLE)}`;
}

export function ArticleRows({
  role,
  items,
  onOpen,
}: {
  role: CatalogRole;
  items: readonly ArticleResponse[];
  onOpen: (articleId: string) => void;
}) {
  return (
    <ListCard label="Articles trouvés">
      {items.map((raw) => {
        const view = articleView(role, raw);
        return (
          <ListCardRow
            key={view.id}
            title={view.name}
            subtitle={subtitle(view)}
            {...(view.archived ? { badge: <ArchivedBadge /> } : {})}
            onOpen={() => {
              onOpen(view.id);
            }}
          />
        );
      })}
    </ListCard>
  );
}
