import { useParams } from "react-router";
import { findSection } from "../core/profile/shopProfile";
import { MORE_KEY } from "../core/profile/types";
import { AccountPage } from "../features/settings/AccountPage";
import { ComingSoon } from "./ComingSoon";
import { NotFoundPage } from "./NotFoundPage";
import { MorePage } from "./MorePage";
import { ACCOUNT_KEY } from "./RoleHome";
import { useActiveShop } from "./shopContext";

/** Écrans communs à tous les rôles, hors barre du bas. */
const SETTINGS_KEY = "reglages";
const ALERTS_KEY = "alertes";

/**
 * `/s/{shopId}/{section}` : une section absente du menu du rôle n'existe pas pour lui
 * (CDC § 1.3 : ce qu'il n'a pas le droit de faire n'apparaît pas du tout).
 */
export function SectionPage() {
  const { section = "" } = useParams();
  const { role, profile } = useActiveShop();
  if (section === ACCOUNT_KEY) return <AccountPage title="Mon compte" />;
  if (section === ALERTS_KEY) return <ComingSoon title="Alertes" />;
  const entry = findSection(profile, role, section);
  if (entry === null) return <NotFoundPage />;
  if (entry.key === MORE_KEY) return <MorePage />;
  if (entry.key === SETTINGS_KEY) return <AccountPage title={entry.label} />;
  return <ComingSoon title={entry.label} />;
}
