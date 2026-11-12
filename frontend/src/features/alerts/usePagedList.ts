import { useState } from "react";
import { NetworkError } from "../../core/api/errors";
import { asError, useLoad, type Loaded } from "../expenses/useLoad";

/** Page d'une liste paginée par curseur (specs § 6.1 : `?cursor=` → `next_cursor`). */
export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
}

export interface PagedList<P extends CursorPage<T>, T> {
  /** État de la **première** page (ses champs annexes, ex. `unread_count`). */
  first: Loaded<P>;
  /** Éléments de toutes les pages lues, dans l'ordre du serveur. */
  items: T[];
  hasMore: boolean;
  loadingMore: boolean;
  /** Vrai si la page suivante n'a pas pu être lue faute de réseau. */
  moreOffline: boolean;
  loadMore: () => void;
  /** Relit depuis la première page. */
  reload: () => void;
}

interface Extra<T> {
  key: string;
  items: T[];
  cursor: string | null;
}

/**
 * Liste paginée relue quand `key` change (filtres). « Voir plus » ajoute la page suivante ;
 * une coupure le dit, toute autre erreur est relancée au rendu (fail-fast, jamais avalée).
 */
export function usePagedList<P extends CursorPage<T>, T>(
  key: string,
  load: (cursor: string | null) => Promise<P>,
): PagedList<P, T> {
  const [round, setRound] = useState(0);
  const fullKey = `${key}|${String(round)}`;
  const first = useLoad(fullKey, () => load(null));
  const [extra, setExtra] = useState<Extra<T> | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreOffline, setMoreOffline] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  if (failure !== null) throw asError(failure);

  const own = extra?.key === fullKey ? extra : null;
  const items = first.status === "ready" ? [...first.value.items, ...(own?.items ?? [])] : [];
  const cursor =
    own === null ? (first.status === "ready" ? first.value.next_cursor : null) : own.cursor;

  const loadMore = () => {
    if (cursor === null) throw new Error("« Voir plus » sans page suivante");
    setLoadingMore(true);
    setMoreOffline(false);
    load(cursor).then(
      (page) => {
        setExtra({
          key: fullKey,
          items: [...(own?.items ?? []), ...page.items],
          cursor: page.next_cursor,
        });
        setLoadingMore(false);
      },
      (error: unknown) => {
        setLoadingMore(false);
        if (error instanceof NetworkError) setMoreOffline(true);
        else setFailure(error);
      },
    );
  };

  return {
    first,
    items,
    hasMore: first.status === "ready" && cursor !== null,
    loadingMore,
    moreOffline,
    loadMore,
    reload: () => {
      setRound((n) => n + 1);
    },
  };
}
