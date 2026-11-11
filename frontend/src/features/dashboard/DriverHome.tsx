import { ListCard, ListCardRow } from "../../shared/ui";
import { FiguresPending } from "./FiguresOffline";
import { laterLot } from "./homeText";
import { useHome } from "./useHome";

/**
 * Accueil du chauffeur (UC-TDB-05) : voyage en cours et dépenses de voyage arrivent au Lot 2 ;
 * l'écran le dit, sans faux zéro (le serveur renvoie `{available: false, lot: 2}`).
 */
export function DriverHome({ shopId }: { shopId: string }) {
  const { loaded, retry } = useHome(shopId, "driver");
  if (loaded.status !== "ready") return <FiguresPending status={loaded.status} onRetry={retry} />;
  const home = loaded.value;
  return (
    <ListCard label="Mon voyage">
      <ListCardRow title="Voyage en cours" subtitle={laterLot(home.current_trip)} />
      <ListCardRow title="Mes dépenses de voyage" subtitle={laterLot(home.trip_expenses)} />
    </ListCard>
  );
}
