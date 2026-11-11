import { useState } from "react";
import { ChevronDown, CirclePlus, ShoppingBag, Users } from "lucide-react";
import type { Purchase } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { formatDate, formatMoney } from "../../shared/format";
import { Button, EmptyState, KpiCard, Skeleton } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import { asError, useLoad } from "../expenses/useLoad";
import { defaultFilters, periodProblem, toQuery, type ListFilters } from "./listFilters";
import { purchaseErrorMessage } from "./purchaseErrors";
import { PurchaseFiltersPanel } from "./PurchaseFiltersPanel";
import { PurchaseRow } from "./PurchaseRow";
import type { ScreenProps } from "./purchasingNav";

const countText = (count: number) =>
  count === 0 ? "Aucun achat" : count === 1 ? "1 achat" : `${String(count)} achats`;

/**
 * Liste des achats (UC-ACH-05) : mois en cours par défaut, totaux de la période en haut
 * (annulés exclus, calculés par le serveur), filtres, lignes par date décroissante,
 * « Afficher plus » (pagination par curseur).
 */
export function PurchaseList({ shopId, refs, nav }: ScreenProps) {
  const { gateway, now } = usePurchasingDeps();
  const today = businessDate(now());
  const [filters, setFilters] = useState<ListFilters>(() => defaultFilters(today));
  const [more, setMore] = useState<{ key: string; items: Purchase[]; cursor: string | null }>();
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const query = periodProblem(filters) === undefined ? toQuery(filters, today) : null;
  const key = JSON.stringify(query);
  const page = useLoad(key, () =>
    query === null ? Promise.resolve(null) : gateway.list(shopId, query),
  );
  const ready = page.status === "ready" ? page.value : null;
  const extra = more?.key === key ? more : undefined;
  const items = ready === null ? [] : [...ready.items, ...(extra?.items ?? [])];
  const cursor = extra === undefined ? (ready?.next_cursor ?? null) : extra.cursor;

  const loadMore = async () => {
    if (query === null || cursor === null) return;
    setMessage(null);
    try {
      const next = await gateway.list(shopId, query, cursor);
      setMore({ key, items: [...(extra?.items ?? []), ...next.items], cursor: next.next_cursor });
    } catch (error) {
      try {
        setMessage(purchaseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    }
  };

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Achats</h1>
      <Button size="lg" fullWidth icon={CirclePlus} onClick={nav.create}>
        Nouvel achat
      </Button>
      <Button variant="secondary" icon={Users} fullWidth onClick={nav.suppliers}>
        Fournisseurs
      </Button>
      <PurchaseFiltersPanel
        shopId={shopId}
        refs={refs}
        value={filters}
        onChange={(patch) => {
          setFilters((current) => ({ ...current, ...patch }));
        }}
      />
      {page.status === "loading" && <Skeleton lines={4} label="Chargement des achats…" />}
      {page.status === "offline" && (
        <EmptyState message="Connexion nécessaire pour afficher les achats." />
      )}
      {ready !== null && (
        <>
          <KpiCard
            label={`Total des achats du ${formatDate(ready.first_day)} au ${formatDate(ready.last_day)}`}
            amount={ready.totals.total}
            detail={`${countText(ready.totals.count)} · marchandise ${formatMoney(ready.totals.merchandise)} · frais ${formatMoney(ready.totals.fees)} · payé ${formatMoney(ready.totals.paid)} (annulés non comptés)`}
          />
          {items.length === 0 ? (
            <EmptyState icon={ShoppingBag} message="Aucun achat sur cette période." />
          ) : (
            <ul
              aria-label="Liste des achats"
              className="m-0 list-none divide-y divide-border overflow-hidden rounded-lg bg-surface p-0 shadow-card"
            >
              {items.map((purchase) => (
                <PurchaseRow key={purchase.id} refs={refs} purchase={purchase} />
              ))}
            </ul>
          )}
          {message !== null && <FormMessage text={message} />}
          {cursor !== null && (
            <Button
              variant="secondary"
              icon={ChevronDown}
              fullWidth
              onClick={() => void loadMore()}
            >
              Afficher plus
            </Button>
          )}
        </>
      )}
    </>
  );
}
