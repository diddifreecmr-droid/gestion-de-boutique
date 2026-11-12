import { useState } from "react";
import { RefreshCw, ScrollText } from "lucide-react";
import type { AuditEntry, AuditPage, JournalMember } from "../../core/gateways/journalContract";
import { useJournalGateway } from "../../core/gateways/httpJournal";
import type { ShopProfile } from "../../core/profile/types";
import { ROLES } from "../../core/auth/me";
import { Button, EmptyState, ListCard, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { MoreButton } from "../alerts/MoreButton";
import { usePagedList } from "../alerts/usePagedList";
import {
  filtersKey,
  NO_FILTERS,
  periodProblem,
  toQuery,
  type JournalFilters,
} from "./journalFilters";
import { JournalFiltersPanel } from "./JournalFiltersPanel";
import { JournalRow } from "./JournalRow";
import type { People } from "./journalText";

function Offline({ what, onRetry }: { what: string; onRetry: () => void }) {
  return (
    <EmptyState
      message={`Connexion nécessaire pour afficher ${what}.`}
      action={
        <Button variant="secondary" icon={RefreshCw} onClick={onRetry}>
          Réessayer
        </Button>
      }
    />
  );
}

function Entries({
  shopId,
  filters,
  people,
}: {
  shopId: string;
  filters: JournalFilters;
  people: People;
}) {
  const gateway = useJournalGateway();
  const query = toQuery(filters);
  const list = usePagedList<AuditPage, AuditEntry>(`${shopId}|${filtersKey(filters)}`, (cursor) =>
    gateway.list(shopId, { ...query, cursor }),
  );
  if (list.first.status === "loading") return <Skeleton lines={4} label="Chargement du journal…" />;
  if (list.first.status === "offline") return <Offline what="le journal" onRetry={list.reload} />;
  if (list.items.length === 0) {
    return <EmptyState icon={ScrollText} message="Aucune action ne correspond à ces filtres." />;
  }
  return (
    <>
      <ListCard label="Entrées du journal">
        {list.items.map((entry) => (
          <JournalRow key={entry.id} entry={entry} people={people} />
        ))}
      </ListCard>
      <MoreButton list={list} />
    </>
  );
}

/** Rôle d'une entrée : libellé du profil ; l'administrateur plateforme n'a pas de rôle de boutique. */
function roleLabelOf(profile: ShopProfile) {
  return (role: string) => {
    const known = ROLES.find((code) => code === role);
    if (known !== undefined) return profile.roleLabel(known);
    return role === "platform_admin" ? "Administrateur plateforme" : role;
  };
}

/**
 * Journal de la boutique (UC-JRN-01) : **lecture seule**, le plus récent en haut, filtres
 * période, utilisateur, type d'action, module. Propriétaire seul (menu « Plus », serveur 403).
 */
export function JournalPage({ shopId, profile }: { shopId: string; profile: ShopProfile }) {
  const gateway = useJournalGateway();
  const [round, setRound] = useState(0);
  const [filters, setFilters] = useState<JournalFilters>(NO_FILTERS);
  const members = useLoad<JournalMember[]>(`${shopId}|${String(round)}`, () =>
    gateway.members(shopId),
  );
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Journal</h1>
      <p className="m-0 text-body text-text-muted">
        Toutes les actions de la boutique, sans modification possible.
      </p>
      {members.status === "loading" && <Skeleton lines={4} label="Chargement du journal…" />}
      {members.status === "offline" && (
        <Offline
          what="le journal"
          onRetry={() => {
            setRound((n) => n + 1);
          }}
        />
      )}
      {members.status === "ready" && (
        <>
          <JournalFiltersPanel
            members={members.value}
            value={filters}
            onChange={(patch) => {
              setFilters((current) => ({ ...current, ...patch }));
            }}
          />
          {periodProblem(filters) === undefined && (
            <Entries
              shopId={shopId}
              filters={filters}
              people={{
                nameOf: (id) => members.value.find((m) => m.user_id === id)?.name,
                roleLabel: roleLabelOf(profile),
              }}
            />
          )}
        </>
      )}
    </>
  );
}
