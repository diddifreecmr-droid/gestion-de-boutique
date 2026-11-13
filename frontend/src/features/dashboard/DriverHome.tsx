import { Truck } from "lucide-react";
import { EmptyState, ListCard, ListCardRow } from "../../shared/ui";
import { FiguresPending } from "./FiguresOffline";
import { laterLot } from "./homeText";
import { useShownBlock } from "./moduleBlock";
import { useHome } from "./useHome";

/** Accueil du chauffeur sans aucun bloc (module `transport` éteint) : ni ligne, ni zéro. */
export const DRIVER_NOTHING = "Rien à suivre ici pour le moment.";

/**
 * Accueil du chauffeur (UC-TDB-05) : voyage en cours et dépenses de voyage arrivent au Lot 2 ;
 * l'écran le dit, sans faux zéro (le serveur renvoie `{available: false, lot: 2}`). Module
 * `transport` éteint : ses blocs valent `null` et n'apparaissent pas (specs § 15.1).
 */
export function DriverHome({ shopId }: { shopId: string }) {
  const shown = useShownBlock();
  const { loaded, retry } = useHome(shopId, "driver");
  if (loaded.status !== "ready") return <FiguresPending status={loaded.status} onRetry={retry} />;
  const trip = shown(loaded.value.current_trip, "transport");
  const expenses = shown(loaded.value.trip_expenses, "transport");
  if (trip === null && expenses === null) {
    return <EmptyState icon={Truck} message={DRIVER_NOTHING} />;
  }
  return (
    <ListCard label="Mon voyage">
      {trip !== null && <ListCardRow title="Voyage en cours" subtitle={laterLot(trip)} />}
      {expenses !== null && (
        <ListCardRow title="Mes dépenses de voyage" subtitle={laterLot(expenses)} />
      )}
    </ListCard>
  );
}
