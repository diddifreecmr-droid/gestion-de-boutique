import { lazy, Suspense } from "react";
import type { PeriodQuery } from "../../../core/gateways/reportingContract";
import { Skeleton } from "../../../shared/ui";
import { FiguresPending } from "../FiguresOffline";
import { queryKey } from "../periods";
import { useFigures, useReporting } from "../reportingContext";
import { Section } from "../Section";
import { MarginGlance } from "./MarginGlance";
import { useWideScreen } from "./useWideScreen";

/** Tableaux, historique et graphiques : chargés à la demande, sur grand écran seulement. */
const MarginsWide = lazy(() => import("./MarginsWide"));

function MarginsFigures({ shopId, query }: { shopId: string; query: PeriodQuery }) {
  const { gateway } = useReporting();
  const wide = useWideScreen();
  const { loaded, retry } = useFigures(`margins:${shopId}:${queryKey(query)}`, () =>
    gateway.margins(shopId, query),
  );
  if (loaded.status !== "ready") {
    return <FiguresPending status={loaded.status} onRetry={retry} />;
  }
  const margins = loaded.value;
  return (
    <>
      <MarginGlance margins={margins} />
      {wide && (
        <Suspense fallback={<Skeleton lines={4} label="Lecture des tableaux…" />}>
          <MarginsWide margins={margins} />
        </Suspense>
      )}
    </>
  );
}

/**
 * « Coûts et marges » du propriétaire (specs § 15.1, design-system § 7.2) : section repliée ;
 * ouverte, elle lit `GET /dashboard/margins` pour la période choisie. Téléphone : chiffres
 * simples ; grand écran (≥ 1024 px) : tableaux triables, historique et graphiques à part.
 */
export function MarginsSection({ shopId, query }: { shopId: string; query: PeriodQuery }) {
  return (
    <Section title="Coûts et marges" summary="Marge par article, taux et meilleurs articles">
      <MarginsFigures shopId={shopId} query={query} />
    </Section>
  );
}
