import { House } from "lucide-react";
import { useNavigate, useParams, useRouteError } from "react-router";
import { isModuleDisabled, MODULE_DISABLED_MESSAGE } from "../core/profile/modules";
import { shopPath } from "../core/profile/shopProfile";
import { Button, EmptyState } from "../shared/ui";

/**
 * Écran d'une boutique interrompu par `403 MODULE_DISABLED` (le module vient d'être éteint par
 * l'administrateur) : message clair, retour à l'accueil. Toute autre erreur est relancée telle
 * quelle (fail-fast) vers l'écran d'erreur de l'application.
 */
export function ModuleErrorPage() {
  const error = useRouteError();
  const navigate = useNavigate();
  const { shopId = "" } = useParams();
  if (!isModuleDisabled(error)) throw error;
  return (
    <EmptyState
      message={MODULE_DISABLED_MESSAGE}
      action={
        <Button variant="secondary" icon={House} onClick={() => void navigate(shopPath(shopId))}>
          Retour à l'accueil
        </Button>
      }
    />
  );
}
