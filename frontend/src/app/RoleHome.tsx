import { lazy, Suspense } from "react";
import { homeEntry } from "../core/profile/shopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { SALE_ROLES } from "../features/sales/saleRoles";
import { Skeleton } from "../shared/ui";
import { useActiveShop } from "./shopContext";

export const ACCOUNT_KEY = "compte";

/** Accueils par rôle (module 14, T22), chargés à la demande. */
const HomeRoute = lazy(() => import("../features/dashboard/HomeRoute"));

/**
 * Accueil de la boutique. Propriétaire et vendeur : page minimale (specs § 15.1), sans titre
 * visible — la barre du haut porte déjà le nom de la boutique ; le titre reste pour les lecteurs
 * d'écran. Comptable et chauffeur : titre et salutation, puis leur accueil. « Mon compte » est
 * dans la barre du haut pour tous les rôles (« Compte », design-system § 6.6).
 */
export function RoleHome() {
  const me = useSignedIn();
  const { shopId, role, profile } = useActiveShop();
  const home = homeEntry(profile);
  const title = home?.label ?? "Accueil";
  const content = (
    <Suspense fallback={<Skeleton lines={4} label="Ouverture de l'accueil…" />}>
      <HomeRoute shopId={shopId} role={role} />
    </Suspense>
  );
  if (SALE_ROLES.includes(role)) {
    return (
      <>
        <h1 className="sr-only">{title}</h1>
        {content}
      </>
    );
  }
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <p className="m-0 text-lead text-text">
        Bonjour {me.name} — {profile.roleLabel(role)}
      </p>
      {content}
    </>
  );
}
