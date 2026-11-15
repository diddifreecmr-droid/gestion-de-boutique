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
import { sellableFirst } from "./articleOrder";
import { articleTitle } from "./articleTitle";
import { inStock, meterStock } from "./draft";
import { articleSearchHint } from "./profileLabels";
import { metersText } from "./textile";
import { capped, statusOf } from "./saleStock";
import { StockStatusBadge } from "./StockStatusBadge";
import { useLookup } from "./useLookup";

/** Nombre d'articles proposés (plus vendus ou résultats). */
export const SEARCH_LIMIT = 8;

export interface ArticlePickerProps {
  shopId: string;
  locationId: string;
  locationName: string;
  /** Aide du champ, selon les champs du profil (« Cherchez par marque ou modèle ») ; neutre par défaut. */
  hint?: string;
  /** Articles déjà dans la vente : non proposés (une ligne par article). */
  excluded: readonly string[];
  onPick: (article: CatalogArticle) => void;
  /** Présent quand la vente a déjà une ligne : referme la recherche. */
  onClose?: () => void;
}

/** Recherche d'article dès la 1re lettre ; champ vide = les plus vendus (CDC § 1.3). */
export function ArticlePicker(props: ArticlePickerProps) {
  const { shopId, locationId, locationName, excluded, onPick, onClose } = props;
  const hint = props.hint ?? articleSearchHint([]);
  const { catalog } = useGateways();
  const [query, setQuery] = useState("");
  const [attempt, setAttempt] = useState(0);
  const lookup = useLookup(`${String(attempt)}:${query}`, () =>
    catalog.searchArticles(shopId, { location_id: locationId, query, limit: SEARCH_LIMIT }),
  );
  const listLabel = query.trim() === "" ? "Les plus vendus" : "Articles trouvés";

  return (
    <section aria-label="Choisir un article" className="flex flex-col gap-4">
      <SearchField label="Article" hint={hint} value={query} onChange={setQuery} />
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
          items={sellableFirst(
            lookup.value.items.filter((article) => !excluded.includes(article.id)),
          )}
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

/**
 * Motos : un article en rupture ne s'ouvre pas (la pastille dit pourquoi). Vente jamais refusée
 * (2026-11-15) : la ligne s'ouvre toujours ; sans chiffre servi, la pastille dit l'état du stock.
 */
function pickState(article: CatalogArticle, onPick: (article: CatalogArticle) => void) {
  const open = {
    onOpen: () => {
      onPick(article);
    },
  };
  if (article.available === null) {
    return { ...open, badge: <StockStatusBadge status={statusOf(article, true)} /> };
  }
  if (inStock(article)) return open;
  const badge = <Badge status="danger">Rupture</Badge>;
  return capped(article) ? { badge } : { ...open, badge };
}

/** Stock du lieu : « 4 », ou en mètres au mètre (« 54,9 m ») ; rien sans chiffre servi. */
function stockOf(article: CatalogArticle, locationName: string): string | undefined {
  if (article.available === null) return undefined;
  const text =
    article.sale_mode === "meter"
      ? metersText(meterStock(article))
      : formatQuantity(article.available);
  return `Stock à ${locationName} : ${text}`;
}

const withSubtitle = (subtitle: string | undefined) => (subtitle === undefined ? {} : { subtitle });

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
      {items.map((article) => (
        <ListCardRow
          key={article.id}
          title={articleTitle(article.name)}
          {...withSubtitle(stockOf(article, locationName))}
          {...(article.base_price === null ? {} : { amount: article.base_price })}
          {...pickState(article, onPick)}
        />
      ))}
    </ListCard>
  );
}
