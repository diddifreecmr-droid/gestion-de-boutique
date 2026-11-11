import { useState } from "react";
import { ChevronDown, CirclePlus, ReceiptText } from "lucide-react";
import { useNavigate } from "react-router";
import { useGateways } from "../../core/gateways/gateways";
import type { SaleResult } from "../../core/gateways/salesContract";
import { shopPath } from "../../core/profile/shopProfile";
import { formatDate, formatMoney } from "../../shared/format";
import { Button, EmptyState, KpiCard, Skeleton } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "./asError";
import { defaultFilters, periodProblem, toQuery, type ListFilters } from "./saleFilters";
import { SaleFiltersPanel } from "./SaleFiltersPanel";
import type { SaleRefs } from "./saleRefs";
import { actionErrorMessage } from "./saleErrorMessage";
import { SaleRow } from "./SaleRow";
import { NEW_SALE_KEY } from "./salesNav";
import { useLookup } from "./useLookup";

const countText = (count: number) =>
  count === 0 ? "Aucune vente" : count === 1 ? "1 vente" : `${String(count)} ventes`;

function periodText(first: string | null, last: string | null): string {
  if (first === null || last === null) return "Toutes dates";
  if (first === last) return `Ventes du ${formatDate(first)}`;
  return `Ventes du ${formatDate(first)} au ${formatDate(last)}`;
}

/**
 * Liste des ventes (UC-VEN-05) : du jour par défaut, plus récentes en haut ; en haut, nombre et
 * total de la période calculés par le serveur (annulations de la période déduites : le total
 * peut être négatif, affiché avec « − »). Le vendeur ne reçoit que ses ventes.
 */
export function SaleList({
  shopId,
  refs,
  title,
}: {
  shopId: string;
  refs: SaleRefs;
  title: string;
}) {
  const { sales } = useGateways();
  const navigate = useNavigate();
  const today = businessDate(new Date());
  const [filters, setFilters] = useState<ListFilters>(() => defaultFilters(today));
  const [more, setMore] = useState<{ key: string; items: SaleResult[]; cursor: string | null }>();
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const query = periodProblem(filters) === undefined ? toQuery(filters, today) : null;
  const key = JSON.stringify(query);
  const page = useLookup(key, () =>
    query === null ? Promise.resolve(null) : sales.listSales(shopId, query, null),
  );
  const ready = page.status === "ready" ? page.value : null;
  const extra = more?.key === key ? more : undefined;
  const items = ready === null ? [] : [...ready.items, ...(extra?.items ?? [])];
  const cursor = extra === undefined ? (ready?.next_cursor ?? null) : extra.cursor;

  const loadMore = async () => {
    if (query === null || cursor === null) return;
    setMessage(null);
    try {
      const next = await sales.listSales(shopId, query, cursor);
      setMore({ key, items: [...(extra?.items ?? []), ...next.items], cursor: next.next_cursor });
    } catch (error) {
      try {
        setMessage(actionErrorMessage(error, "Chargement"));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    }
  };

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <Button
        size="lg"
        fullWidth
        icon={CirclePlus}
        onClick={() => void navigate(shopPath(shopId, NEW_SALE_KEY))}
      >
        Nouvelle vente
      </Button>
      <SaleFiltersPanel
        refs={refs}
        value={filters}
        onChange={(patch) => {
          setFilters((current) => ({ ...current, ...patch }));
        }}
      />
      {page.status === "loading" && <Skeleton lines={4} label="Chargement des ventes…" />}
      {page.status === "offline" && (
        <EmptyState message="Connexion nécessaire pour afficher les ventes." />
      )}
      {ready !== null && (
        <>
          <KpiCard
            label={periodText(ready.first_day, ready.last_day)}
            amount={ready.totals.total}
            detail={`${countText(ready.totals.count)} · encaissé ${formatMoney(ready.totals.paid)} (annulations déduites)`}
          />
          {items.length === 0 ? (
            <EmptyState icon={ReceiptText} message="Aucune vente sur cette période." />
          ) : (
            <ul
              aria-label="Liste des ventes"
              className="m-0 list-none divide-y divide-border overflow-hidden rounded-lg bg-surface p-0 shadow-card"
            >
              {items.map((sale) => (
                <SaleRow key={sale.id} refs={refs} sale={sale} today={today} />
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
