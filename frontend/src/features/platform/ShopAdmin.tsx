import { useState } from "react";
import { ArrowLeft, Lock, RefreshCw, RotateCcw } from "lucide-react";
import type { AdministerShop, ShopAccess, ShopSummary } from "../../core/gateways/platformContract";
import { usePlatformGateway } from "../../core/gateways/httpPlatform";
import { formatDate } from "../../shared/format";
import { Badge, Button, ConfirmDialog, EmptyState, Skeleton } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError, useLoad } from "../expenses/useLoad";
import { isStale, platformErrorMessage, STATUS_LABELS, type PlatformNav } from "./platformNav";
import { ShopModules } from "./ShopModules";
import { ShopRights } from "./ShopRights";

interface Sheet {
  shop: ShopSummary;
  access: ShopAccess;
}

/**
 * Fiche d'une boutique dans la console (TR-23) : identité, statut (fermer / rouvrir), modules,
 * droits d'offre et délégation. Aucune donnée métier de la boutique n'est lue ici.
 */
export function ShopAdmin({ shopId, nav }: { shopId: string; nav: PlatformNav }) {
  const gateway = usePlatformGateway();
  const [round, setRound] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const sheet = useLoad<Sheet>(`${shopId}|${String(round)}`, async () => {
    const [shop, access] = await Promise.all([gateway.get(shopId), gateway.access(shopId)]);
    return { shop, access };
  });

  const administer = async (change: AdministerShop) => {
    setConfirming(false);
    setBusy(true);
    setMessage(null);
    try {
      await gateway.administer(shopId, change);
      setRound((n) => n + 1); // relit statut et droits en vigueur
    } catch (error) {
      try {
        setMessage(platformErrorMessage(error));
        if (isStale(error)) setRound((n) => n + 1); // modifiée ailleurs : la fiche est relue
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  const back = (
    <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
      Retour aux boutiques
    </Button>
  );
  if (sheet.status === "loading") {
    return (
      <>
        {back}
        <Skeleton lines={4} label="Chargement de la boutique…" />
      </>
    );
  }
  if (sheet.status === "offline") {
    return (
      <>
        {back}
        <EmptyState
          message="Connexion nécessaire pour afficher la boutique."
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
      </>
    );
  }
  const { shop, access } = sheet.value;
  const open = shop.status === "active";
  return (
    <>
      {back}
      <div className="flex flex-col items-start gap-2">
        <h1 className="m-0 break-words text-title font-bold text-text">{shop.name}</h1>
        <Badge status={open ? "success" : "danger"}>
          {STATUS_LABELS[shop.status] ?? shop.status}
        </Badge>
        <p className="m-0 text-body text-text-muted">
          {shop.city} · compte {shop.account_name} · offre {shop.plan}
        </p>
        <p className="m-0 text-body text-text-muted">Ouverte le {formatDate(shop.created_at)}</p>
      </div>
      {message !== null && <FormMessage text={message} />}
      {open ? (
        <Button
          variant="danger"
          icon={Lock}
          fullWidth
          loading={busy}
          onClick={() => {
            setConfirming(true);
          }}
        >
          Fermer la boutique
        </Button>
      ) : (
        <Button
          variant="secondary"
          icon={RotateCcw}
          fullWidth
          loading={busy}
          onClick={() => void administer({ status: "active" })}
        >
          Rouvrir la boutique
        </Button>
      )}
      <ShopModules
        key={`${String(round)}|${shop.enabled_modules.join(",")}`}
        enabled={shop.enabled_modules}
        busy={busy}
        onSave={(modules) => void administer({ modules, ...versionOf(shop) })}
      />
      <ShopRights
        access={access}
        busy={busy}
        onOverride={(code, value) => void administer({ entitlements: { [code]: value } })}
      />
      <ConfirmDialog
        open={confirming}
        title={`Fermer ${shop.name} ?`}
        confirmLabel="Fermer"
        confirmIcon={Lock}
        onConfirm={() => void administer({ status: "closed" })}
        onCancel={() => {
          setConfirming(false);
        }}
      >
        Ses membres ne pourront plus l'ouvrir ; ses données sont gardées et elle peut être rouverte.
      </ConfirmDialog>
    </>
  );
}

/**
 * Version de la boutique lue, renvoyée pour refuser un enregistrement sur une fiche périmée
 * (409 `VERSION_CONFLICT`), dès que le contrat la porte ; sans elle, rien n'est ajouté.
 */
function versionOf(shop: ShopSummary): { version?: number } {
  return "version" in shop && typeof shop.version === "number" ? { version: shop.version } : {};
}
