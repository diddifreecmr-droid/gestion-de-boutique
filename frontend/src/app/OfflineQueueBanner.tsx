import { useEffect, useSyncExternalStore } from "react";
import { CloudUpload, AlertTriangle } from "lucide-react";
import { useParams } from "react-router";
import { useServices } from "../core/services/servicesContext";
import { Banner } from "../shared/ui";

function plural(count: number): string {
  return count === 1
    ? "1 saisie en attente d'envoi"
    : `${String(count)} saisies en attente d'envoi`;
}

/**
 * File hors connexion de la boutique ouverte (RG-T23, specs § 6.5) — **rien** tant que le
 * droit `offline_capture` est inactif (V1). Droit actif : envoie la file à l'ouverture et au
 * retour du réseau, affiche « N saisies en attente d'envoi », les saisies refusées avec leur
 * motif (gardées sur l'appareil) et les arrivées « Vente V-HL-… → V-000125 ».
 */
export function OfflineQueueBanner() {
  const { offline } = useServices();
  const { shopId = "" } = useParams();
  const enabled = useSyncExternalStore(offline.rights.subscribe, () =>
    offline.rights.isEnabled(shopId),
  );
  const state = useSyncExternalStore(offline.state.subscribe, offline.state.get);
  useEffect(
    () => (enabled ? offline.watch(shopId, window) : undefined),
    [enabled, offline, shopId],
  );
  if (!enabled) return null;
  const pending = state.pending[shopId] ?? 0;
  const rejected = state.rejected[shopId] ?? [];
  return (
    <>
      {pending > 0 && <Banner title={plural(pending)} icon={CloudUpload} />}
      {rejected.map((entry) => (
        <Banner key={entry.number} title={`Saisie ${entry.number} refusée`} icon={AlertTriangle}>
          {entry.message}
        </Banner>
      ))}
      {state.failure !== null && (
        <Banner title="Envoi des saisies impossible" icon={AlertTriangle}>
          {state.failure}
        </Banner>
      )}
      {state.arrived.length > 0 && (
        <Banner title="Saisies envoyées" icon={CloudUpload}>
          {state.arrived.join(" · ")}
        </Banner>
      )}
    </>
  );
}
