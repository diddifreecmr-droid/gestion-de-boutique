import { useState } from "react";
import { Pencil, Tag } from "lucide-react";
import type { ArticleForm, ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { Button, useToast } from "../../shared/ui";
import { ArchiveAction } from "./ArchiveAction";
import { ArchivedBadge } from "./ArchivedBadge";
import { ArticleEditForm } from "./ArticleEditForm";
import { ArticleFacts } from "./ArticleFacts";
import { articleView } from "./articleView";
import { catalogRights, type CatalogRole } from "./catalogRights";
import { PriceHistoryList } from "./PriceHistoryList";
import { PricesForm } from "./PricesForm";

export interface ArticleSheetProps {
  shopId: string;
  role: CatalogRole;
  article: ArticleResponse;
  form: ArticleForm;
  onChanged: (article: ArticleResponse) => void;
  onReload: () => void;
  onOpenArticle: (articleId: string) => void;
}

type Mode = "view" | "edit" | "prices";

/** Fiche d'un article chargé : lecture, puis une tâche à la fois (P1). */
export function ArticleSheet(props: ArticleSheetProps) {
  const { shopId, role, form, onReload } = props;
  const toast = useToast();
  const [mode, setMode] = useState<Mode>("view");
  const view = articleView(role, props.article);
  const rights = catalogRights(role);
  const back = () => {
    setMode("view");
  };
  const saved = (message: string) => (article: ArticleResponse) => {
    toast.show({ tone: "success", message });
    props.onChanged(article);
  };

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="m-0 text-title font-bold text-text">{view.name}</h1>
        {view.archived && <ArchivedBadge />}
      </div>
      {mode === "edit" && (
        <ArticleEditForm
          shopId={shopId}
          view={view}
          fields={form.fields}
          onSaved={saved("Article enregistré")}
          onCancel={back}
          onOpenExisting={props.onOpenArticle}
          onReload={onReload}
        />
      )}
      {mode === "prices" && view.kind === "owner" && (
        <PricesForm
          shopId={shopId}
          article={view}
          minPriceEnabled={form.minPriceEnabled}
          onSaved={saved("Prix enregistrés")}
          onCancel={back}
          onReload={onReload}
        />
      )}
      {mode === "view" && (
        <>
          <ArticleFacts view={view} fields={form.fields} />
          {rights.edit && (
            <Button
              variant="secondary"
              fullWidth
              icon={Pencil}
              onClick={() => {
                setMode("edit");
              }}
            >
              Modifier l'article
            </Button>
          )}
          {rights.setPrices && (
            <Button
              variant="secondary"
              fullWidth
              icon={Tag}
              onClick={() => {
                setMode("prices");
              }}
            >
              Modifier les prix
            </Button>
          )}
          {view.kind === "owner" && view.history !== null && (
            <PriceHistoryList history={view.history} />
          )}
          {rights.archive && (
            <ArchiveAction
              shopId={shopId}
              view={view}
              onDone={props.onChanged}
              onReload={onReload}
            />
          )}
        </>
      )}
    </>
  );
}
