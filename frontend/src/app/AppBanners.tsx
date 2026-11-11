import { Download, RefreshCw } from "lucide-react";
import { installWaitingUpdate, useUpdateReady } from "../core/pwa/appUpdate";
import { useIsOnline } from "../core/services/servicesContext";
import { Banner, Button } from "../shared/ui";

/**
 * États durables (§ 6.5), sous la barre du haut : « Connexion nécessaire » (aucune mise en
 * file, TR-26) et « Nouvelle version disponible » (specs § 7.3).
 */
export function AppBanners() {
  const online = useIsOnline();
  const updateReady = useUpdateReady();
  return (
    <>
      {!online && (
        <Banner title="Connexion nécessaire">
          Vérifiez le réseau. Votre saisie reste à l'écran : renvoyez-la d'un appui.
        </Banner>
      )}
      {updateReady && (
        <Banner
          title="Nouvelle version disponible"
          icon={Download}
          action={
            <Button variant="secondary" icon={RefreshCw} onClick={installWaitingUpdate}>
              Mettre à jour
            </Button>
          }
        />
      )}
    </>
  );
}
