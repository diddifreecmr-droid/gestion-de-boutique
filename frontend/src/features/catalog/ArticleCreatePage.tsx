import { RefreshCw } from "lucide-react";
import { useState } from "react";
import type { ArticleForm, ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button, EmptyState, Skeleton, useToast } from "../../shared/ui";
import { ArticleCreateForm } from "./ArticleCreateForm";
import { loadFailureMessage } from "./catalogErrors";
import type { CatalogRole } from "./catalogRights";
import { InlineMessage } from "./InlineMessage";
import { useLoad } from "./useLoad";

export interface ArticleCreatePageProps {
  shopId: string;
  role: CatalogRole;
  /** Ouvre la fiche (article créé, ou article existant proposé après un doublon). */
  onOpenArticle: (articleId: string) => void;
}

/** UC-STK-01 « Nouvel article » : le formulaire suit les champs du profil de la boutique. */
export function ArticleCreatePage({ shopId, role, onOpenArticle }: ArticleCreatePageProps) {
  const gateway = useCatalogAdmin();
  const toast = useToast();
  const [attempt, setAttempt] = useState(0);
  const [load] = useLoad<ArticleForm>(`${String(attempt)}|${shopId}`, () =>
    gateway.articleForm(shopId),
  );
  const created = (article: ArticleResponse) => {
    toast.show({ tone: "success", message: `Article créé : ${article.display_name}` });
    onOpenArticle(article.id);
  };
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Nouvel article</h1>
      {load.status === "loading" && <Skeleton lines={3} label="Préparation du formulaire…" />}
      {load.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour créer un article."
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
      {load.status === "failed" && <InlineMessage text={loadFailureMessage(load.error)} />}
      {load.status === "ready" && (
        <ArticleCreateForm
          shopId={shopId}
          role={role}
          form={load.value}
          onCreated={created}
          onOpenExisting={onOpenArticle}
        />
      )}
    </>
  );
}
