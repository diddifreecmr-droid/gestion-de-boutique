import { useMemo } from "react";
import { createHttpJournal, JournalContext } from "../../core/gateways/httpJournal";
import type { ShopProfile } from "../../core/profile/types";
import { useServices } from "../../core/services/servicesContext";
import { JournalPage } from "./JournalPage";

/** Entrée de route « Journal » (« Plus » du propriétaire, chargée à la demande). */
export default function JournalRoute({
  shopId,
  profile,
}: {
  shopId: string;
  profile: ShopProfile;
}) {
  const services = useServices();
  const gateway = useMemo(() => createHttpJournal(services), [services]);
  return (
    <JournalContext.Provider value={gateway}>
      <JournalPage shopId={shopId} profile={profile} />
    </JournalContext.Provider>
  );
}
