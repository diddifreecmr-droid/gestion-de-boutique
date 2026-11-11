import { CirclePlus, Wallet } from "lucide-react";
import { useNavigate } from "react-router";
import { shopPath } from "../../core/profile/shopProfile";
import { Badge, Button, ListCard, ListCardRow } from "../../shared/ui";
import { PAY_SEARCH, RECEIVABLES_KEY } from "../receivables/receivablesNav";
import { MY_SALES_KEY, NEW_SALE_KEY } from "../sales/salesNav";
import { FiguresPending } from "./FiguresOffline";
import { count } from "./homeText";
import { useHome } from "./useHome";

function SellerFigures({ shopId }: { shopId: string }) {
  const navigate = useNavigate();
  const { loaded, retry } = useHome(shopId, "seller");
  if (loaded.status !== "ready") return <FiguresPending status={loaded.status} onRetry={retry} />;
  const home = loaded.value;
  return (
    <ListCard label="Ma journée">
      <ListCardRow
        title="Mes ventes du jour"
        subtitle={count(home.sales_count, "vente", "ventes", "Aucune vente aujourd'hui")}
        amount={home.sales_amount}
        onOpen={() => void navigate(shopPath(shopId, MY_SALES_KEY))}
      />
      <ListCardRow
        title="Mes rappels du jour"
        subtitle={count(
          home.reminders_due,
          "client à relancer",
          "clients à relancer",
          "Aucun rappel aujourd'hui",
        )}
        {...(home.reminders_due > 0 ? { badge: <Badge status="credit">À relancer</Badge> } : {})}
        onOpen={() => void navigate(shopPath(shopId, RECEIVABLES_KEY))}
      />
      <ListCardRow
        title="Saisies en attente d'envoi"
        subtitle={count(
          home.pending_uploads,
          "saisie à envoyer",
          "saisies à envoyer",
          "Aucune saisie en attente",
        )}
      />
    </ListCard>
  );
}

/**
 * Accueil du vendeur (UC-TDB-05) : « Nouvelle vente » en gros, « Versement », puis sa journée.
 * Le bloc `seller` de `GET /home` n'a ni marge ni coût (RG-D02) : rien de tel n'est affiché.
 */
export function SellerHome({ shopId }: { shopId: string }) {
  const navigate = useNavigate();
  return (
    <>
      <Button
        size="lg"
        fullWidth
        icon={CirclePlus}
        onClick={() => void navigate(shopPath(shopId, NEW_SALE_KEY))}
      >
        Nouvelle vente
      </Button>
      <Button
        variant="secondary"
        size="lg"
        fullWidth
        icon={Wallet}
        onClick={() => void navigate(`${shopPath(shopId, RECEIVABLES_KEY)}${PAY_SEARCH}`)}
      >
        Versement
      </Button>
      <SellerFigures shopId={shopId} />
    </>
  );
}
