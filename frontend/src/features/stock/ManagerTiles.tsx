import { ClipboardList, Coins, PackageX, SlidersHorizontal } from "lucide-react";
import { ActionTile, ActionTileGrid } from "../../shared/ui";
import type { StockNav } from "./stockNav";

/** Actions du propriétaire et du comptable sur le stock (UC-STK-07, 08, 10). */
export function ManagerTiles({ nav }: { nav: StockNav }) {
  return (
    <nav aria-label="Actions sur le stock">
      <ActionTileGrid>
        <ActionTile
          icon={SlidersHorizontal}
          label="Ajustement"
          onClick={() => {
            nav.adjustment();
          }}
        />
        <ActionTile
          icon={ClipboardList}
          label="Inventaire"
          onClick={() => {
            nav.inventory();
          }}
        />
        <ActionTile icon={Coins} label="Valeur du stock" onClick={nav.value} />
        <ActionTile icon={PackageX} label="Stock abîmé" onClick={nav.damaged} />
      </ActionTileGrid>
    </nav>
  );
}
