import { useState } from "react";
import type {
  ArticleResponse,
  ArticleStatusFilter,
} from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { useCatalogSubmit } from "./useCatalogSubmit";
import { useLoad } from "./useLoad";

/** Taille d'une page de la liste (« Afficher plus » charge la suivante). */
export const PAGE_SIZE = 20;

interface Page {
  items: ArticleResponse[];
  next: string | null;
}

/**
 * Liste paginée par curseur : la 1re page est relue à chaque lettre ou filtre (seule la
 * dernière réponse compte) ; « Afficher plus » ajoute la page suivante à la suite.
 */
export function useArticlePages(shopId: string, text: string, status: ArticleStatusFilter) {
  const gateway = useCatalogAdmin();
  const [attempt, setAttempt] = useState(0);
  const key = `${String(attempt)}|${status}|${text.trim()}`;
  const [first, replace] = useLoad<Page>(key, async () => {
    const page = await gateway.listArticles(shopId, {
      text,
      status,
      cursor: null,
      limit: PAGE_SIZE,
    });
    return { items: page.items, next: page.next_cursor };
  });
  const more = useCatalogSubmit();

  function loadMore() {
    if (first.status !== "ready" || first.value.next === null) {
      throw new Error("« Afficher plus » sans page suivante");
    }
    const { items, next } = first.value;
    void more.run(
      () => gateway.listArticles(shopId, { text, status, cursor: next, limit: PAGE_SIZE }),
      (page) => {
        replace({ items: [...items, ...page.items], next: page.next_cursor });
      },
    );
  }

  return {
    first,
    loadMore,
    loadingMore: more.pending,
    moreFailure: more.failure,
    retry: () => {
      setAttempt((n) => n + 1);
    },
  };
}
