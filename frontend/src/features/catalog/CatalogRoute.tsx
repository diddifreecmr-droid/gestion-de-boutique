import { ArrowLeft } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router";
import type { Role } from "../../core/auth/me";
import { CatalogAdminProvider } from "../../core/gateways/CatalogAdminProvider";
import { Button } from "../../shared/ui";
import { ArticleCreatePage } from "./ArticleCreatePage";
import { ArticleSheetPage } from "./ArticleSheetPage";
import { CatalogListPage } from "./CatalogListPage";
import {
  ARTICLE_PARAM,
  articlePath,
  catalogListPath,
  FABRIC_PARAM,
  fabricPath,
  NEW_ARTICLE,
  NEW_FABRIC,
} from "./catalogPaths";
import { FabricCreatePage } from "./FabricCreatePage";
import { FabricPage } from "./FabricPage";
import { catalogRights, catalogRole, type CatalogRole } from "./catalogRights";

/**
 * Entrée de route (chargée à la demande) de la section « Stock » pour le propriétaire et le
 * comptable : liste, fiche (`?article={id}`) ou création (`?article=nouveau`).
 */
export default function CatalogRoute({ shopId, role }: { shopId: string; role: Role }) {
  return (
    <CatalogAdminProvider>
      <CatalogScreen shopId={shopId} role={catalogRole(role)} />
    </CatalogAdminProvider>
  );
}

function CatalogScreen({ shopId, role }: { shopId: string; role: CatalogRole }) {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const article = search.get(ARTICLE_PARAM);
  const fabric = search.get(FABRIC_PARAM);
  const open = (id: string) => void navigate(articlePath(shopId, id));
  const back = () => void navigate(catalogListPath(shopId));
  const backButton = (
    <Button variant="ghost" icon={ArrowLeft} onClick={back}>
      Retour aux articles
    </Button>
  );
  if (fabric !== null) {
    return (
      <>
        {backButton}
        <FabricPage key={fabric} shopId={shopId} role={role} fabric={fabric} onOpenArticle={open} />
      </>
    );
  }
  if (article === null) return <CatalogListPage shopId={shopId} role={role} />;
  if (article === NEW_FABRIC) {
    if (!catalogRights(role).edit) throw new Error(`Création de tissu refusée au rôle ${role}`);
    return (
      <>
        {backButton}
        <FabricCreatePage
          shopId={shopId}
          role={role}
          onOpenArticle={open}
          onOpenFabric={(name) => void navigate(fabricPath(shopId, name), { replace: true })}
        />
      </>
    );
  }
  if (article === NEW_ARTICLE) {
    // Le comptable crée aussi (UC-STK-01) ; un rôle sans ce droit n'arrive pas jusqu'ici.
    if (!catalogRights(role).edit) throw new Error(`Création d'article refusée au rôle ${role}`);
    return (
      <>
        {backButton}
        <ArticleCreatePage
          shopId={shopId}
          role={role}
          onOpenArticle={(id) => void navigate(articlePath(shopId, id), { replace: true })}
        />
      </>
    );
  }
  return (
    <>
      {backButton}
      <ArticleSheetPage
        key={article}
        shopId={shopId}
        role={role}
        articleId={article}
        onOpenArticle={open}
      />
    </>
  );
}
