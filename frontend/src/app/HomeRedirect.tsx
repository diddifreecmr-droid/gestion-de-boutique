import { Navigate } from "react-router";
import { useSignedIn } from "../core/services/servicesContext";
import { shopPath } from "../core/profile/shopProfile";
import { EmptyState } from "../shared/ui";
import { PLATFORM_PATH, SHOP_PICKER_PATH } from "./paths";

/** `/` : console pour l'administrateur, sinon la boutique (ou la liste s'il y en a plusieurs). */
export function HomeRedirect() {
  const me = useSignedIn();
  if (me.isPlatformAdmin) return <Navigate to={PLATFORM_PATH} replace />;
  const [first, ...others] = me.shops;
  if (first === undefined) {
    return (
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
        <h1 className="m-0 text-title font-bold text-text">Aucune boutique</h1>
        <EmptyState message="Votre compte n'est rattaché à aucune boutique. Contactez le propriétaire." />
      </main>
    );
  }
  return <Navigate to={others.length === 0 ? shopPath(first.shopId) : SHOP_PICKER_PATH} replace />;
}
