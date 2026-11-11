import { ArrowLeft } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router";
import type { Role } from "../../core/auth/me";
import { CatalogAdminProvider } from "../../core/gateways/CatalogAdminProvider";
import { Button } from "../../shared/ui";
import { ArticleCreatePage } from "./ArticleCreatePage";
import { ArticleSheetPage } from "./ArticleSheetPage";
import { CatalogListPage } from "./CatalogListPage";
import { ARTICLE_PARAM, articlePath, catalogListPath, NEW_ARTICLE } from "./catalogPaths";
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
  if (article === null) return <CatalogListPage shopId={shopId} role={role} />;

  const open = (id: string) => void navigate(articlePath(shopId, id));
  const back = () => void navigate(catalogListPath(shopId));
  const backButton = (
    <Button variant="ghost" icon={ArrowLeft} onClick={back}>
      Retour aux articles
    </Button>
  );
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
