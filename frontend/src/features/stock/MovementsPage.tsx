import { useState } from "react";
import { ChevronDown, ExternalLink, SlidersHorizontal } from "lucide-react";
import { useNavigate } from "react-router";
import type { Movement } from "../../core/gateways/stockContract";
import { useStockGateway } from "../../core/gateways/httpStock";
import { useSignedIn } from "../../core/services/servicesContext";
import { Button, EmptyState } from "../../shared/ui";
import { articlePath } from "../catalog/catalogPaths";
import { MovementRow } from "./MovementRow";
import { BackButton, ErrorText, LoadPending, ScreenTitle } from "./Notice";
import { useStockNav } from "./stockNav";
import type { ManagerRole } from "./stockRoles";
import { asError, useLoad } from "./useLoad";
import { NetworkError } from "../../core/api/errors";

export interface MovementsPageProps {
  shopId: string;
  role: ManagerRole;
  articleId: string;
}

interface More {
  items: readonly Movement[];
  next: string | null;
}

/**
 * Fiche stock d'un article (UC-STK-06, propriétaire et comptable) : mouvements du plus récent
 * au plus ancien (date, type, lieu, ±quantité, stock après, document lié, auteur), par pages.
 */
export function MovementsPage({ shopId, role, articleId }: MovementsPageProps) {
  const gateway = useStockGateway();
  const me = useSignedIn();
  const nav = useStockNav();
  const navigate = useNavigate();
  const { load, retry } = useLoad(`${shopId}|${articleId}`, async () => {
    const [name, members, page] = await Promise.all([
      gateway.articleName(shopId, articleId),
      role === "owner" ? gateway.members(shopId) : Promise.resolve([]),
      gateway.movements(shopId, articleId, null),
    ]);
    return { name, page, members: new Map(members.map((m) => [m.user_id, m.name])) };
  });
  const [more, setMore] = useState<More | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);
  const [crash, setCrash] = useState<unknown>(null);
  if (crash !== null) throw asError(crash);

  const back = <BackButton label="Retour au stock" onClick={nav.matrix} />;
  if (load.status !== "ready") {
    return (
      <>
        {back}
        <ScreenTitle>Historique</ScreenTitle>
        <LoadPending load={load} label="Chargement de l'historique…" onRetry={retry} />
      </>
    );
  }
  const { name, page, members } = load.value;
  const items = [...page.items, ...(more?.items ?? [])];
  const next = more === null ? page.next_cursor : more.next;
  /** Auteur : son nom pour le propriétaire ; « vous » ou « un autre membre » pour le comptable. */
  const author = (userId: string) =>
    userId === me.userId ? me.name : (members.get(userId) ?? "un autre membre");

  const loadMore = () => {
    if (next === null || loadingMore) return;
    setLoadingMore(true);
    setMoreError(null);
    gateway.movements(shopId, articleId, next).then(
      (found) => {
        setLoadingMore(false);
        setMore({ items: [...(more?.items ?? []), ...found.items], next: found.next_cursor });
      },
      (error: unknown) => {
        setLoadingMore(false);
        if (error instanceof NetworkError)
          setMoreError("Connexion nécessaire pour afficher la suite.");
        else setCrash(error);
      },
    );
  };

  return (
    <>
      {back}
      <ScreenTitle>{name}</ScreenTitle>
      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="secondary"
          icon={SlidersHorizontal}
          onClick={() => {
            nav.adjustment(articleId);
          }}
        >
          Ajuster
        </Button>
        <Button
          variant="secondary"
          icon={ExternalLink}
          onClick={() => void navigate(articlePath(shopId, articleId))}
        >
          Fiche article
        </Button>
      </div>
      <h2 className="m-0 text-title-sm font-semibold text-text">Mouvements</h2>
      {items.length === 0 ? (
        <EmptyState message="Aucun mouvement pour cet article." />
      ) : (
        <ul
          aria-label="Mouvements de stock"
          className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card"
        >
          {items.map((movement) => (
            <MovementRow
              key={movement.id}
              movement={movement}
              unit={page.stock_unit}
              author={author(movement.author_id)}
            />
          ))}
        </ul>
      )}
      {moreError !== null && <ErrorText text={moreError} />}
      {next !== null && (
        <Button
          variant="secondary"
          fullWidth
          icon={ChevronDown}
          loading={loadingMore}
          onClick={loadMore}
        >
          Afficher plus
        </Button>
      )}
    </>
  );
}
