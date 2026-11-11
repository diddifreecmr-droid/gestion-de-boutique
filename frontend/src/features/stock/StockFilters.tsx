import type { MatrixOrder, StockColumn } from "../../core/gateways/stockContract";
import { ChoiceChips, Disclosure } from "../../shared/ui";

/** Valeur « tous les lieux » du filtre (aucun `location_id`). */
export const ALL_LOCATIONS = "tous";

const SORTS = [
  { value: "name", label: "Par nom" },
  { value: "quantity_asc", label: "Moins en stock" },
  { value: "quantity_desc", label: "Plus en stock" },
] as const satisfies readonly { value: MatrixOrder; label: string }[];

export interface StockFiltersProps {
  locations: readonly StockColumn[];
  locationId: string;
  onLocation: (locationId: string) => void;
  sort: MatrixOrder;
  onSort: (sort: MatrixOrder) => void;
}

/** Filtre par lieu et tri par quantité (UC-STK-05), repliés sous « Filtrer et trier » (P4). */
export function StockFilters({
  locations,
  locationId,
  onLocation,
  sort,
  onSort,
}: StockFiltersProps) {
  const options = [
    { value: ALL_LOCATIONS, label: "Tous les lieux" },
    ...locations.map((location) => ({ value: location.location_id, label: location.name })),
  ];
  const open = locationId !== ALL_LOCATIONS || sort !== "name";
  return (
    <Disclosure label="Filtrer et trier" defaultOpen={open}>
      <ChoiceChips label="Lieu" options={options} value={locationId} onChange={onLocation} />
      <ChoiceChips label="Trier" options={SORTS} value={sort} onChange={onSort} />
    </Disclosure>
  );
}
