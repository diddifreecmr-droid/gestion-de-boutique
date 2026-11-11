import { useState } from "react";
import { RefreshCw, X } from "lucide-react";
import type { CatalogArticle } from "../../core/gateways/catalogContract";
import { useGateways } from "../../core/gateways/gateways";
import { formatQuantity } from "../../shared/format";
import {
  Badge,
  Button,
  EmptyState,
  ListCard,
  ListCardRow,
  SearchField,
  Skeleton,
} from "../../shared/ui";
import { unitStock } from "./draft";
import { useLookup } from "./useLookup";

/** Nombre d'articles proposés (plus vendus ou résultats). */
export const SEARCH_LIMIT = 8;

export interface ArticlePickerProps {
  shopId: string;
  locationId: string;
  locationName: string;
  /** Articles déjà dans la vente : non proposés (une ligne par article). */
  excluded: readonly string[];
  onPick: (article: CatalogArticle) => void;
  /** Présent quand la vente a déjà une ligne : referme la recherche. */
  onClose?: () => void;
}

/** Recherche d'article dès la 1re lettre ; champ vide = les plus vendus (CDC § 1.3). */
export function ArticlePicker(props: ArticlePickerProps) {
  const { shopId, locationId, locationName, excluded, onPick, onClose } = props;
  const { catalog } = useGateways();
  const [query, setQuery] = useState("");
  const [attempt, setAttempt] = useState(0);
  const lookup = useLookup(`${String(attempt)}:${query}`, () =>
    catalog.searchArticles(shopId, { location_id: locationId, query, limit: SEARCH_LIMIT }),
  );
  const listLabel = query.trim() === "" ? "Les plus vendus" : "Articles trouvés";

  return (
    <section aria-label="Choisir un article" className="flex flex-col gap-4">
      <SearchField
        label="Article"
        hint="Tapez les premières lettres du modèle"
        value={query}
        onChange={setQuery}
      />
      {lookup.status === "loading" && <Skeleton lines={3} label="Recherche des articles…" />}
      {lookup.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour chercher un article."
          action={
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={() => {
                setAttempt((n) => n + 1);
              }}
            >
              Réessayer
            </Button>
          }
        />
      )}
      {lookup.status === "ready" && (
        <Results
          label={listLabel}
          query={query}
          items={lookup.value.items.filter((article) => !excluded.includes(article.id))}
          locationName={locationName}
          onPick={onPick}
        />
      )}
      {onClose !== undefined && (
        <Button variant="ghost" icon={X} fullWidth onClick={onClose}>
          Fermer la recherche
        </Button>
      )}
    </section>
  );
}

function Results({
  label,
  query,
  items,
  locationName,
  onPick,
}: {
  label: string;
  query: string;
  items: CatalogArticle[];
  locationName: string;
  onPick: (article: CatalogArticle) => void;
}) {
  if (items.length === 0) {
    const text = query.trim();
    return (
      <EmptyState
        message={
          text === ""
            ? "Tapez le nom d'un article pour le trouver."
            : `Aucun article ne correspond à « ${text} ».`
        }
      />
    );
  }
  return (
    <ListCard label={label}>
      {items.map((article) => {
        const stock = unitStock(article);
        return (
          <ListCardRow
            key={article.id}
            title={article.name}
            subtitle={`Stock à ${locationName} : ${formatQuantity(stock)}`}
            amount={article.base_price}
            {...(stock < 1
              ? { badge: <Badge status="danger">Rupture</Badge> }
              : {
                  onOpen: () => {
                    onPick(article);
                  },
                })}
          />
        );
      })}
    </ListCard>
  );
}
