import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { ArticleForm, ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { ArticleRows } from "./ArticleRows";
import { loadFailureMessage } from "./catalogErrors";
import { catalogRights, type CatalogRole } from "./catalogRights";
import { FabricAddColors } from "./FabricAddColors";
import { FabricEditForm } from "./FabricEditForm";
import { InlineMessage } from "./InlineMessage";
import { useLoad } from "./useLoad";

export interface FabricPageProps {
  shopId: string;
  role: CatalogRole;
  fabric: string;
  onOpenArticle: (articleId: string) => void;
}

interface FabricData {
  form: ArticleForm;
  colors: ArticleResponse[];
}

/** Couleurs listées au plus sur la page d'un tissu. */
const COLOR_LIMIT = 100;

/**
 * Page d'un tissu (Textile, 2026-11-15) : ses couleurs (un article chacune), « Ajouter une
 * couleur », et « Modifier le tissu » qui s'applique à toutes les couleurs.
 */
export function FabricPage({ shopId, role, fabric, onOpenArticle }: FabricPageProps) {
  const gateway = useCatalogAdmin();
  const [attempt, setAttempt] = useState(0);
  const [load, replace] = useLoad<FabricData>(`${String(attempt)}|${fabric}`, async () => {
    const [form, list] = await Promise.all([
      gateway.articleForm(shopId),
      gateway.listArticles(shopId, {
        text: "",
        status: "active",
        cursor: null,
        limit: COLOR_LIMIT,
        fabric,
      }),
    ]);
    return { form, colors: list.items };
  });
  const rights = catalogRights(role);
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{fabric}</h1>
      {load.status === "loading" && <Skeleton lines={3} label="Chargement du tissu…" />}
      {load.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour afficher le tissu."
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
        <FabricDetail
          shopId={shopId}
          role={role}
          fabric={fabric}
          data={load.value}
          edit={rights.edit}
          onOpenArticle={onOpenArticle}
          onColors={(colors) => {
            replace({ ...load.value, colors });
          }}
        />
      )}
    </>
  );
}

function FabricDetail(
  props: Omit<FabricPageProps, "onOpenArticle"> & {
    data: FabricData;
    edit: boolean;
    onOpenArticle: (articleId: string) => void;
    onColors: (colors: ArticleResponse[]) => void;
  },
) {
  const { shopId, role, fabric, data, onColors } = props;
  const [sample] = data.colors;
  if (sample === undefined) {
    return <EmptyState message={`Aucune couleur active pour le tissu « ${fabric} ».`} />;
  }
  return (
    <>
      <ArticleRows
        role={role}
        label={`Couleurs de ${fabric}`}
        items={data.colors}
        onOpen={props.onOpenArticle}
      />
      {props.edit && (
        <FabricAddColors shopId={shopId} fabric={fabric} colors={data.colors} onAdded={onColors} />
      )}
      {props.edit && (
        <FabricEditForm
          key={data.colors.map((c) => `${c.id}:${String(c.version)}`).join("|")}
          shopId={shopId}
          role={role}
          fabric={fabric}
          form={data.form}
          sample={sample}
          onSaved={onColors}
        />
      )}
    </>
  );
}
