import { useState } from "react";
import { Archive, ArchiveRestore } from "lucide-react";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button, ConfirmDialog, useToast } from "../../shared/ui";
import type { ArticleView } from "./articleView";
import { SubmitFailureNotice } from "./SubmitFailureNotice";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface ArchiveActionProps {
  shopId: string;
  view: ArticleView;
  onDone: (article: ArticleResponse) => void;
  onReload: () => void;
}

/**
 * UC-STK-04 (propriétaire) : archiver ou réactiver, après confirmation. Un article qui a
 * encore du stock est refusé par le serveur (`ARTICLE_HAS_STOCK`) : le message le dit.
 */
export function ArchiveAction({ shopId, view, onDone, onReload }: ArchiveActionProps) {
  const gateway = useCatalogAdmin();
  const toast = useToast();
  const submit = useCatalogSubmit();
  const [open, setOpen] = useState(false);
  const archiving = !view.archived;

  function confirm() {
    setOpen(false);
    void submit.run(
      () =>
        archiving
          ? gateway.archiveArticle(shopId, view.id)
          : gateway.reactivateArticle(shopId, view.id),
      (article) => {
        toast.show({
          tone: "success",
          message: archiving ? `Article archivé : ${view.name}` : `Article réactivé : ${view.name}`,
        });
        onDone(article);
      },
    );
  }

  return (
    <>
      <Button
        variant={archiving ? "danger" : "secondary"}
        fullWidth
        icon={archiving ? Archive : ArchiveRestore}
        loading={submit.pending}
        onClick={() => {
          submit.clear();
          setOpen(true);
        }}
      >
        {archiving ? "Archiver l'article" : "Réactiver l'article"}
      </Button>
      {submit.failure !== null && (
        <SubmitFailureNotice
          failure={submit.failure}
          onOpenExisting={() => {
            throw new Error("Un archivage ne peut pas produire de doublon");
          }}
          onReload={onReload}
        />
      )}
      <ConfirmDialog
        open={open}
        title={archiving ? `Archiver « ${view.name} » ?` : `Réactiver « ${view.name} » ?`}
        confirmLabel={archiving ? "Archiver" : "Réactiver"}
        confirmIcon={archiving ? Archive : ArchiveRestore}
        onConfirm={confirm}
        onCancel={() => {
          setOpen(false);
        }}
      >
        {archiving
          ? "Il disparaîtra des listes de vente et d'achat, mais restera dans l'historique et les rapports."
          : "Il reviendra dans les listes de vente et d'achat."}
      </ConfirmDialog>
    </>
  );
}
