import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { ArticleForm, ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { ArticleSheet } from "./ArticleSheet";
import { loadFailureMessage } from "./catalogErrors";
import type { CatalogRole } from "./catalogRights";
import { InlineMessage } from "./InlineMessage";
import { useLoad, type Load } from "./useLoad";

export interface ArticleSheetPageProps {
  shopId: string;
  role: CatalogRole;
  articleId: string;
  onOpenArticle: (articleId: string) => void;
}

interface SheetData {
  article: ArticleResponse;
  form: ArticleForm;
}

/** Fiche article : lecture (avec les droits du rôle), puis modification, prix, archivage. */
export function ArticleSheetPage(props: ArticleSheetPageProps) {
  const { shopId, articleId } = props;
  const gateway = useCatalogAdmin();
  const [attempt, setAttempt] = useState(0);
  const [load, replace] = useLoad<SheetData>(`${String(attempt)}|${articleId}`, async () => {
    const [article, form] = await Promise.all([
      gateway.getArticle(shopId, articleId),
      gateway.articleForm(shopId),
    ]);
    return { article, form };
  });
  const reload = () => {
    setAttempt((n) => n + 1);
  };
  return <SheetState {...props} load={load} replace={replace} reload={reload} />;
}

function SheetState({
  load,
  replace,
  reload,
  ...props
}: ArticleSheetPageProps & {
  load: Load<SheetData>;
  replace: (data: SheetData) => void;
  reload: () => void;
}) {
  switch (load.status) {
    case "loading":
      return <Skeleton lines={5} label="Ouverture de l'article…" />;
    case "offline":
      return (
        <EmptyState
          message="Connexion nécessaire pour ouvrir cet article."
          action={
            <Button variant="secondary" icon={RefreshCw} onClick={reload}>
              Réessayer
            </Button>
          }
        />
      );
    case "failed":
      return <InlineMessage text={loadFailureMessage(load.error)} />;
    case "ready":
      return (
        <ArticleSheet
          {...props}
          key={`${load.value.article.id}-${String(load.value.article.version)}`}
          article={load.value.article}
          form={load.value.form}
          onChanged={(article) => {
            replace({ article, form: load.value.form });
          }}
          onReload={reload}
        />
      );
  }
}
