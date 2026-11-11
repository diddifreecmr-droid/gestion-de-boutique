import { useState } from "react";
import { X } from "lucide-react";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { Button, Skeleton } from "../../shared/ui";
import { ArticleCreateForm } from "../catalog/ArticleCreateForm";
import { purchaseErrorMessage } from "./purchaseErrors";
import { FormMessage } from "../expenses/FormMessage";
import { asError, useLoad } from "../expenses/useLoad";
import type { PurchaseRole } from "./purchasingNav";

export interface ArticleCreatePanelProps {
  shopId: string;
  role: PurchaseRole;
  onCreated: (article: ArticleResponse) => void;
  onClose: () => void;
}

/**
 * « Créer l'article » dans le flux de la saisie d'achat : réutilise le formulaire du catalogue
 * (champs du profil, `id` client idempotent, doublon proposé). Le doublon « Ouvrir … » choisit
 * l'article existant au lieu d'ouvrir sa fiche : on reste sur l'achat.
 */
export function ArticleCreatePanel({ shopId, role, onCreated, onClose }: ArticleCreatePanelProps) {
  const { catalog } = usePurchasingDeps();
  const [attempt, setAttempt] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const form = useLoad(`${shopId}:${String(attempt)}`, () => catalog.articleForm(shopId));

  const pickExisting = async (articleId: string) => {
    setMessage(null);
    try {
      onCreated(await catalog.getArticle(shopId, articleId));
    } catch (error) {
      try {
        setMessage(purchaseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    }
  };

  return (
    <section
      aria-label="Nouvel article"
      className="flex flex-col gap-4 rounded-lg border border-border-strong p-4"
    >
      <h2 className="m-0 text-title-sm font-semibold text-text">Nouvel article</h2>
      {form.status === "loading" && <Skeleton lines={3} label="Préparation du formulaire…" />}
      {form.status === "offline" && (
        <>
          <FormMessage text="Connexion nécessaire pour créer un article." />
          <Button
            variant="secondary"
            onClick={() => {
              setAttempt((n) => n + 1);
            }}
          >
            Réessayer
          </Button>
        </>
      )}
      {form.status === "ready" && (
        <ArticleCreateForm
          shopId={shopId}
          role={role}
          form={form.value}
          onCreated={onCreated}
          onOpenExisting={(id) => void pickExisting(id)}
        />
      )}
      {message !== null && <FormMessage text={message} />}
      <Button variant="ghost" icon={X} onClick={onClose}>
        Revenir à la recherche
      </Button>
    </section>
  );
}
