import { useState } from "react";
import type { MatrixOrder, StockColumn } from "../../core/gateways/stockContract";
import { useStockGateway } from "../../core/gateways/httpStock";
import { useActiveProfile } from "../../core/profile/activeProfile";
import { listSearchHint } from "../../core/profile/vocabulary";
import { EmptyState, ListCard, SearchField } from "../../shared/ui";
import { LoadPending, ScreenTitle } from "./Notice";
import { StockItem } from "./StockItem";
import { ALL_LOCATIONS, StockFilters } from "./StockFilters";
import { StockTools } from "./StockTools";
import { useStockNav } from "./stockNav";
import { isManager, type StockRole } from "./stockRoles";
import { stockLine } from "./stockView";
import { useLoad } from "./useLoad";

export interface StockMatrixPageProps {
  shopId: string;
  role: StockRole;
}

/**
 * Matrice de stock (UC-STK-05) : une ligne compacte par article (nom, total, pastille), le
 * détail par lieu, les prix et les coûts à un appui ; recherche dès la 1re lettre (`?q=`),
 * filtre par lieu, tri par quantité ; outils du gestionnaire repliés. Écran d'arrivée de la
 * section « Stock » des trois rôles concernés (audit UX du 13/11/2026 : la liste au 1er écran).
 */
export function StockMatrixPage({ shopId, role }: StockMatrixPageProps) {
  const gateway = useStockGateway();
  const nav = useStockNav();
  const profile = useActiveProfile();
  const [text, setText] = useState("");
  const [locationId, setLocationId] = useState(ALL_LOCATIONS);
  const [sort, setSort] = useState<MatrixOrder>("name");
  /** Lieux de la boutique, retenus de la dernière lecture sans filtre (les choix restent). */
  const [places, setPlaces] = useState<readonly StockColumn[]>([]);
  const filter = locationId === ALL_LOCATIONS ? null : locationId;
  const { load, retry } = useLoad(`${shopId}|${text.trim()}|${locationId}|${sort}`, () =>
    gateway.matrix(shopId, { text, locationId: filter, sort }),
  );
  if (load.status === "ready" && filter === null && load.value.locations !== places) {
    setPlaces(load.value.locations);
  }
  const manager = isManager(role);

  return (
    <>
      <ScreenTitle>Stock</ScreenTitle>
      <SearchField
        label="Rechercher un article"
        hint={listSearchHint(profile.articleFields)}
        value={text}
        onChange={setText}
      />
      <StockFilters
        locations={places}
        locationId={locationId}
        onLocation={setLocationId}
        sort={sort}
        onSort={setSort}
      />
      {manager && <StockTools nav={nav} />}
      {load.status !== "ready" && (
        <LoadPending load={load} label="Chargement du stock…" onRetry={retry} />
      )}
      {load.status === "ready" && load.value.items.length === 0 && (
        <EmptyState
          message={
            text.trim() === ""
              ? "Aucun article en stock pour l'instant."
              : `Aucun article ne correspond à « ${text.trim()} ».`
          }
        />
      )}
      {load.status === "ready" && load.value.items.length > 0 && (
        <ListCard label="Stock par article">
          {load.value.items.map((raw) => {
            const line = stockLine(role, raw, load.value.locations);
            return (
              <StockItem
                key={line.articleId}
                line={line}
                {...(manager
                  ? {
                      onHistory: () => {
                        nav.movements(line.articleId);
                      },
                    }
                  : {})}
              />
            );
          })}
        </ListCard>
      )}
    </>
  );
}
