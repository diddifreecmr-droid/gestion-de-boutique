import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { ArticleForm, FabricResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button, EmptyState, Skeleton, useToast } from "../../shared/ui";
import { loadFailureMessage } from "./catalogErrors";
import type { CatalogRole } from "./catalogRights";
import { FabricCreateForm } from "./FabricCreateForm";
import { InlineMessage } from "./InlineMessage";
import { useLoad } from "./useLoad";

export interface FabricCreatePageProps {
  shopId: string;
  role: CatalogRole;
  /** Ouvre la page du tissu créé. */
  onOpenFabric: (fabric: string) => void;
  onOpenArticle: (articleId: string) => void;
}

/** Écran « Nouveau tissu » : réglage « prix minimum » lu du profil, puis le formulaire. */
export function FabricCreatePage({
  shopId,
  role,
  onOpenFabric,
  onOpenArticle,
}: FabricCreatePageProps) {
  const gateway = useCatalogAdmin();
  const toast = useToast();
  const [attempt, setAttempt] = useState(0);
  const [load] = useLoad<ArticleForm>(`${String(attempt)}|${shopId}`, () =>
    gateway.articleForm(shopId),
  );
  const created = (fabric: FabricResponse) => {
    const count = fabric.items.length;
    const colors = count > 1 ? `${String(count)} couleurs` : "1 couleur";
    toast.show({ tone: "success", message: `Tissu créé : ${fabric.fabric} (${colors})` });
    onOpenFabric(fabric.fabric);
  };
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Nouveau tissu</h1>
      {load.status === "loading" && <Skeleton lines={3} label="Préparation du formulaire…" />}
      {load.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour créer un tissu."
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
        <FabricCreateForm
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
