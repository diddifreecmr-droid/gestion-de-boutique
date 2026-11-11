import { useState } from "react";
import type { MatrixOrder, StockColumn } from "../../core/gateways/stockContract";
import { useStockGateway } from "../../core/gateways/httpStock";
import { EmptyState, SearchField } from "../../shared/ui";
import { ManagerTiles } from "./ManagerTiles";
import { LoadPending, ScreenTitle } from "./Notice";
import { StockCard } from "./StockCard";
import { ALL_LOCATIONS, StockFilters } from "./StockFilters";
import { useStockNav } from "./stockNav";
import { isManager, type StockRole } from "./stockRoles";
import { stockLine } from "./stockView";
import { useLoad } from "./useLoad";

export interface StockMatrixPageProps {
  shopId: string;
  role: StockRole;
}

/**
 * Matrice de stock (UC-STK-05) : un article par carte, un lieu par ligne dans l'ordre des
 * lieux, « En route », « Total » ; recherche dès la 1re lettre (`?q=`), filtre par lieu, tri
 * par quantité. Écran d'arrivée de la section « Stock » des trois rôles concernés.
 */
export function StockMatrixPage({ shopId, role }: StockMatrixPageProps) {
  const gateway = useStockGateway();
  const nav = useStockNav();
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
      {manager && <ManagerTiles nav={nav} />}
      <SearchField
        label="Rechercher un article"
        hint="Nom, marque, modèle ou référence"
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
        <ul aria-label="Stock par article" className="m-0 flex list-none flex-col gap-4 p-0">
          {load.value.items.map((raw) => {
            const line = stockLine(role, raw, load.value.locations);
            return (
              <StockCard
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
        </ul>
      )}
    </>
  );
}
