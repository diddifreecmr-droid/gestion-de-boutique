import { useState } from "react";
import { ChevronDown, CirclePlus, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router";
import type { ArticleStatusFilter } from "../../core/gateways/catalogAdminContract";
import {
  Button,
  ChoiceChips,
  Disclosure,
  EmptyState,
  SearchField,
  Skeleton,
} from "../../shared/ui";
import { ArticleRows } from "./ArticleRows";
import { loadFailureMessage } from "./catalogErrors";
import { articlePath, newArticlePath } from "./catalogPaths";
import { catalogRights, type CatalogRole } from "./catalogRights";
import { useActiveProfile } from "../../core/profile/activeProfile";
import { listSearchHint } from "../../core/profile/vocabulary";
import { InlineMessage } from "./InlineMessage";
import { useArticlePages } from "./useArticlePages";

const FILTERS = [
  { value: "active", label: "Actifs" },
  { value: "archived", label: "Archivés" },
  { value: "all", label: "Tous" },
] as const satisfies readonly { value: ArticleStatusFilter; label: string }[];

export interface CatalogListPageProps {
  shopId: string;
  role: CatalogRole;
}

/** Liste des articles (UC-STK-01 à 04) : recherche dès la 1re lettre, filtre, « Afficher plus ». */
export function CatalogListPage({ shopId, role }: CatalogListPageProps) {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [status, setStatus] = useState<ArticleStatusFilter>("active");
  const pages = useArticlePages(shopId, text, status);
  const profile = useActiveProfile();
  const { first } = pages;

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Articles</h1>
      {catalogRights(role).edit && (
        <Button
          size="lg"
          fullWidth
          icon={CirclePlus}
          onClick={() => void navigate(newArticlePath(shopId))}
        >
          Nouvel article
        </Button>
      )}
      <SearchField
        label="Rechercher un article"
        hint={listSearchHint(profile.articleFields)}
        value={text}
        onChange={setText}
      />
      {/* Filtre replié (audit UX du 13/11/2026) : la liste des articles reste au 1er écran. */}
      <Disclosure label="Filtrer" defaultOpen={status !== "active"}>
        <ChoiceChips label="Afficher" options={FILTERS} value={status} onChange={setStatus} />
      </Disclosure>
      {first.status === "loading" && <Skeleton lines={3} label="Chargement des articles…" />}
      {first.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour afficher les articles."
          action={
            <Button variant="secondary" icon={RefreshCw} onClick={pages.retry}>
              Réessayer
            </Button>
          }
        />
      )}
      {first.status === "failed" && <InlineMessage text={loadFailureMessage(first.error)} />}
      {first.status === "ready" && first.value.items.length === 0 && (
        <EmptyState message={emptyMessage(text, status)} />
      )}
      {first.status === "ready" && first.value.items.length > 0 && (
        <>
          <ArticleRows
            role={role}
            items={first.value.items}
            onOpen={(id) => void navigate(articlePath(shopId, id))}
          />
          {pages.moreFailure?.kind === "message" && <InlineMessage text={pages.moreFailure.text} />}
          {first.value.next !== null && (
            <Button
              variant="secondary"
              fullWidth
              icon={ChevronDown}
              loading={pages.loadingMore}
              onClick={pages.loadMore}
            >
              Afficher plus
            </Button>
          )}
        </>
      )}
    </>
  );
}

function emptyMessage(text: string, status: ArticleStatusFilter): string {
  const typed = text.trim();
  if (typed !== "") return `Aucun article ne correspond à « ${typed} ».`;
  if (status === "archived") return "Aucun article archivé.";
  return "Aucun article pour l'instant.";
}
