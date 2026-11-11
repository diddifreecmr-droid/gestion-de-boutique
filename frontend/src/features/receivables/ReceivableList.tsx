import { useState } from "react";
import { FilePlus, HandCoins, Wallet } from "lucide-react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import { Button, EmptyState, KpiCard, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { DEFAULT_FILTERS, toQuery, type ListFilters } from "./filters";
import { ReceivableFiltersPanel } from "./ReceivableFiltersPanel";
import { ReceivableRow } from "./ReceivableRow";
import type { ScreenProps } from "./receivablesNav";

const debtorsText = (count: number) =>
  count === 0 ? "Aucun client" : count === 1 ? "1 client" : `${String(count)} clients`;

/** Chiffre clé qui n'est pas un montant (nombre de clients), au gabarit de `KpiCard`. */
function CountCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-surface p-4 shadow-card">
      <span className="text-body text-text-muted">{label}</span>
      <span className="text-kpi font-bold tabular-nums text-text">{value}</span>
    </div>
  );
}

/**
 * Liste des créances (UC-CRE-04) : trois chiffres du serveur en haut, filtres, puis la liste
 * complète triée par reste décroissant (ordre du serveur, sans pagination).
 */
export function ReceivableList({ shopId, refs, nav }: ScreenProps) {
  const { gateway } = useReceivablesDeps();
  const [filters, setFilters] = useState<ListFilters>(DEFAULT_FILTERS);
  const query = toQuery(filters);
  const listing = useLoad(JSON.stringify(query), () => gateway.list(shopId, query));
  const ready = listing.status === "ready" ? listing.value : null;
  const owner = refs.me.role === "owner";
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Créances</h1>
      <Button
        size="lg"
        fullWidth
        icon={Wallet}
        onClick={() => {
          nav.pay();
        }}
      >
        Enregistrer un versement
      </Button>
      {owner && (
        <Button variant="ghost" icon={FilePlus} onClick={nav.legacy}>
          Créance ancienne
        </Button>
      )}
      {listing.status === "loading" && <Skeleton lines={4} label="Chargement des créances…" />}
      {listing.status === "offline" && (
        <EmptyState message="Connexion nécessaire pour afficher les créances." />
      )}
      {ready !== null && (
        <>
          <KpiCard label="Total à recevoir" amount={ready.summary.total_due} />
          <CountCard label="Clients débiteurs" value={debtorsText(ready.summary.debtor_count)} />
          <KpiCard label="Versements reçus aujourd'hui" amount={ready.summary.received_today} />
        </>
      )}
      <ReceivableFiltersPanel
        refs={refs}
        value={filters}
        onChange={(patch) => {
          setFilters((current) => ({ ...current, ...patch }));
        }}
      />
      {ready !== null &&
        (ready.items.length === 0 ? (
          <EmptyState icon={HandCoins} message="Aucune créance pour ces filtres." />
        ) : (
          <ul
            aria-label="Liste des créances"
            className="m-0 list-none divide-y divide-border overflow-hidden rounded-lg bg-surface p-0 shadow-card"
          >
            {ready.items.map((receivable) => (
              <ReceivableRow key={receivable.id} receivable={receivable} />
            ))}
          </ul>
        ))}
    </>
  );
}
