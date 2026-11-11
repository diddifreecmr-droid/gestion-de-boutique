import { useStockGateway } from "../../core/gateways/httpStock";
import { AdjustmentForm } from "./AdjustmentForm";
import { BackButton, ErrorText, LoadPending, ScreenTitle } from "./Notice";
import { useStockNav } from "./stockNav";
import { useLoad } from "./useLoad";

/**
 * Ajustement ponctuel (UC-STK-08) : les lieux et les articles viennent de la matrice (articles
 * actifs, lieux actifs dans l'ordre). `articleId` présélectionne l'article (depuis sa fiche).
 */
export function AdjustmentPage({
  shopId,
  articleId,
}: {
  shopId: string;
  articleId: string | null;
}) {
  const gateway = useStockGateway();
  const nav = useStockNav();
  const { load, retry } = useLoad(`${shopId}|adjust`, () =>
    gateway.matrix(shopId, { text: "", locationId: null, sort: "name" }),
  );
  const back = <BackButton label="Retour au stock" onClick={nav.matrix} />;
  if (load.status !== "ready") {
    return (
      <>
        {back}
        <ScreenTitle>Ajustement de stock</ScreenTitle>
        <LoadPending load={load} label="Chargement des lieux et des articles…" onRetry={retry} />
      </>
    );
  }
  const { locations, items } = load.value;
  const preselected =
    articleId === null ? null : (items.find((row) => row.article_id === articleId) ?? null);
  return (
    <>
      {back}
      <ScreenTitle>Ajustement de stock</ScreenTitle>
      {articleId !== null && preselected === null && (
        <ErrorText text="Cet article n'est plus actif : choisissez-en un autre." />
      )}
      {locations.length === 0 ? (
        <ErrorText text="Aucun lieu actif dans cette boutique : créez d'abord un lieu." />
      ) : (
        <AdjustmentForm
          shopId={shopId}
          locations={locations}
          articles={items}
          preselected={preselected}
          onDone={nav.movements}
        />
      )}
    </>
  );
}
