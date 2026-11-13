import { ClipboardList, Coins, PackageX, SlidersHorizontal } from "lucide-react";
import { Button, Disclosure } from "../../shared/ui";
import type { StockNav } from "./stockNav";

/**
 * Outils du propriétaire et du comptable sur le stock (UC-STK-07, 08, 10), repliés sous
 * « Outils du stock » (audit UX du 13/11/2026) : la liste des articles reste au premier
 * écran, les outils sont à un appui. Tous relèvent du module `catalog` (toujours actif).
 */
export function StockTools({ nav }: { nav: StockNav }) {
  return (
    <Disclosure label="Outils du stock">
      <nav aria-label="Outils du stock" className="grid grid-cols-2 gap-2">
        <Button
          variant="secondary"
          fullWidth
          icon={SlidersHorizontal}
          onClick={() => {
            nav.adjustment();
          }}
        >
          Ajustement
        </Button>
        <Button
          variant="secondary"
          fullWidth
          icon={ClipboardList}
          onClick={() => {
            nav.inventory();
          }}
        >
          Inventaire
        </Button>
        <Button variant="secondary" fullWidth icon={Coins} onClick={nav.value}>
          Valeur du stock
        </Button>
        <Button variant="secondary" fullWidth icon={PackageX} onClick={nav.damaged}>
          Stock abîmé
        </Button>
      </nav>
    </Disclosure>
  );
}
