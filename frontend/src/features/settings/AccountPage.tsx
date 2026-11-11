import { useState } from "react";
import { KeyRound, LogOut, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router";
import { reloadLatestVersion } from "../../core/pwa/reload";
import { APP_VERSION } from "../../core/pwa/version";
import { useServices, useSession, useSignedIn } from "../../core/services/servicesContext";
import { Button, ConfirmDialog, ListCard, ListCardRow, useToast } from "../../shared/ui";
import { CHANGE_PIN_PATH } from "../auth/ChangePinPage";
import { DiscardQueueDialogs } from "./DiscardQueueDialogs";

export interface AccountPageProps {
  title: string;
  /** Injectable pour les tests ; par défaut vide les caches et recharge (specs § 7.3). */
  reload?: () => Promise<void>;
}

/**
 * PROVISOIRE (T12) — « Mon compte » / Réglages : version de l'application, « Recharger la
 * dernière version », changement de code, déconnexion — bloquée tant que des saisies hors
 * connexion attendent, sauf double confirmation (RG-T24, T23 ; jamais en V1). Les réglages de la boutique (UC-SOC-06)
 * arrivent avec T22.
 */
export function AccountPage({ title, reload = reloadLatestVersion }: AccountPageProps) {
  const me = useSignedIn();
  const session = useSession();
  const { offline } = useServices();
  const [waiting, setWaiting] = useState(0);
  const toast = useToast();
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState(false);
  const [reloading, setReloading] = useState(false);
  const fail = (what: string) => (error: unknown) => {
    toast.show({
      tone: "error",
      message: `${what} : ${error instanceof Error ? error.message : String(error)}`,
    });
  };

  return (
    <div className="flex flex-col gap-5">
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <ListCard label="Compte et application">
        <ListCardRow title={me.name} subtitle={me.phone} />
        <ListCardRow title="Version de l'application" subtitle={APP_VERSION} />
      </ListCard>
      <Button
        variant="secondary"
        fullWidth
        icon={RefreshCw}
        loading={reloading}
        onClick={() => {
          setReloading(true);
          reload().catch((error: unknown) => {
            setReloading(false);
            fail("Rechargement impossible")(error);
          });
        }}
      >
        Recharger la dernière version
      </Button>
      <Button
        variant="secondary"
        fullWidth
        icon={KeyRound}
        onClick={() => void navigate(CHANGE_PIN_PATH)}
      >
        {me.isPlatformAdmin ? "Changer mon mot de passe" : "Changer mon code"}
      </Button>
      <Button
        variant="ghost"
        fullWidth
        icon={LogOut}
        onClick={() => {
          // V1 (aucun droit hors connexion) : confirmation simple, sans rien lire.
          if (offline.rights.enabledShops().length === 0) {
            setConfirming(true);
            return;
          }
          offline.waiting().then((count) => {
            if (count === 0) setConfirming(true);
            else setWaiting(count);
          }, fail("Lecture des saisies en attente impossible"));
        }}
      >
        Se déconnecter
      </Button>
      <ConfirmDialog
        open={confirming}
        title="Se déconnecter ?"
        confirmLabel="Se déconnecter"
        confirmIcon={LogOut}
        onCancel={() => {
          setConfirming(false);
        }}
        onConfirm={() => {
          setConfirming(false);
          session.logout().catch(fail("Déconnexion impossible"));
        }}
      >
        Il faudra votre numéro et votre code pour revenir sur cet appareil.
      </ConfirmDialog>
      <DiscardQueueDialogs
        count={waiting}
        onCancel={() => {
          setWaiting(0);
        }}
        onDiscard={() => {
          setWaiting(0);
          offline
            .discard()
            .then(() => session.logout())
            .catch(fail("Déconnexion impossible"));
        }}
      />
    </div>
  );
}
