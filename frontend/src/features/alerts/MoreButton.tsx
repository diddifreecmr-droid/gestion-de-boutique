import { ChevronDown } from "lucide-react";
import { Button } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import type { CursorPage, PagedList } from "./usePagedList";

/** « Voir plus » d'une liste paginée, et le message si la suite n'a pas pu être lue. */
export function MoreButton<P extends CursorPage<T>, T>({ list }: { list: PagedList<P, T> }) {
  if (!list.hasMore) return null;
  return (
    <>
      {list.moreOffline && <FormMessage text="Connexion nécessaire pour lire la suite." />}
      <Button
        variant="secondary"
        icon={ChevronDown}
        fullWidth
        loading={list.loadingMore}
        onClick={list.loadMore}
      >
        Voir plus
      </Button>
    </>
  );
}
