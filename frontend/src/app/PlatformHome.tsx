import { TopBar, useToast } from "../shared/ui";
import { AccountPage } from "../features/settings/AccountPage";
import { useSignedIn } from "../core/services/servicesContext";
import { NotFoundPage } from "./NotFoundPage";
import { AppBanners } from "./AppBanners";
import { ComingSoon } from "./ComingSoon";

/**
 * PROVISOIRE (T12) — console de l'administrateur plateforme. L'API `/platform/*` (T10)
 * n'existe pas encore : seuls le compte et la version sont proposés.
 */
export function PlatformHome() {
  const me = useSignedIn();
  const toast = useToast();
  if (!me.isPlatformAdmin) return <NotFoundPage />;
  return (
    <div className="min-h-screen">
      <TopBar
        title="Console plateforme"
        alertCount={0}
        onAlertsClick={() => {
          toast.show({
            tone: "success",
            message: "Les alertes de la plateforme arrivent bientôt.",
          });
        }}
      />
      <AppBanners />
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
        <ComingSoon title="Boutiques" />
        <AccountPage title="Mon compte" />
      </main>
    </div>
  );
}
