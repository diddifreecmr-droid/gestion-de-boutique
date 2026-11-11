import { CirclePlus, Construction } from "lucide-react";
import { useNavigate } from "react-router";
import { shopPath } from "../../core/profile/shopProfile";
import { Button, EmptyState } from "../../shared/ui";

/** Segment d'URL de l'écran « Nouvelle vente » (clé du menu vendeur, CDC § 17.4). */
export const NEW_SALE_KEY = "nouvelle-vente";
/** Entrée « Ventes » du propriétaire. */
export const SALES_KEY = "ventes";

/**
 * PROVISOIRE (T21) — « Ventes » du propriétaire : la liste arrive avec `GET /sales` ; en
 * attendant, l'entrée mène à « Nouvelle vente ».
 */
export function SalesHome({ shopId, title }: { shopId: string; title: string }) {
  const navigate = useNavigate();
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <Button
        size="lg"
        fullWidth
        icon={CirclePlus}
        onClick={() => void navigate(shopPath(shopId, NEW_SALE_KEY))}
      >
        Nouvelle vente
      </Button>
      <EmptyState icon={Construction} message="La liste des ventes arrive bientôt." />
    </>
  );
}
