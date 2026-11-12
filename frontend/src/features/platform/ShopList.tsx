import { useState } from "react";
import { CirclePlus, RefreshCw, Store } from "lucide-react";
import { usePlatformGateway } from "../../core/gateways/httpPlatform";
import { formatDate } from "../../shared/format";
import { Badge, Button, EmptyState, ListCard, ListCardRow, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { STATUS_LABELS, type PlatformNav } from "./platformNav";

/** Boutiques de la plateforme (TR-23) : nom, ville, compte, statut ; « Ouvrir une boutique ». */
export function ShopList({ nav }: { nav: PlatformNav }) {
  const gateway = usePlatformGateway();
  const [round, setRound] = useState(0);
  const shops = useLoad(`shops|${String(round)}`, () => gateway.list());
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Boutiques</h1>
      <Button size="lg" fullWidth icon={CirclePlus} onClick={nav.create}>
        Ouvrir une boutique
      </Button>
      {shops.status === "loading" && <Skeleton lines={3} label="Chargement des boutiques…" />}
      {shops.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour afficher les boutiques."
          action={
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={() => {
                setRound((n) => n + 1);
              }}
            >
              Réessayer
            </Button>
          }
        />
      )}
      {shops.status === "ready" && shops.value.length === 0 && (
        <EmptyState icon={Store} message="Aucune boutique pour l'instant." />
      )}
      {shops.status === "ready" && shops.value.length > 0 && (
        <ListCard label="Liste des boutiques">
          {shops.value.map((shop) => (
            <ListCardRow
              key={shop.shop_id}
              title={shop.name}
              subtitle={`${shop.city} · ${shop.account_name} · depuis le ${formatDate(shop.created_at)}`}
              badge={
                shop.status === "active" ? undefined : (
                  <Badge status="danger">{STATUS_LABELS[shop.status] ?? shop.status}</Badge>
                )
              }
              onOpen={() => {
                nav.open(shop.shop_id);
              }}
            />
          ))}
        </ListCard>
      )}
    </>
  );
}
