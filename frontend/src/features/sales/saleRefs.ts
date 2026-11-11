/**
 * Référentiels de la liste et de la fiche : lieux (points de vente) et modes de paiement
 * (`saleSetup`), noms des membres pour le propriétaire (`GET /members`, refusé au vendeur).
 */
import type { CatalogGateway } from "../../core/gateways/catalogContract";
import type { SaleMember, SalesGateway } from "../../core/gateways/salesContract";
import type { SaleRole } from "./salesNav";

export interface SaleRefs {
  role: SaleRole;
  userId: string;
  locations: readonly { id: string; name: string }[];
  modes: readonly { id: string; name: string }[];
  /** Vide pour le vendeur (il ne voit que ses ventes). */
  members: readonly SaleMember[];
}

export async function loadSaleRefs(
  gateways: { catalog: CatalogGateway; sales: SalesGateway },
  shopId: string,
  who: { role: SaleRole; userId: string },
): Promise<SaleRefs> {
  const [setup, members] = await Promise.all([
    gateways.catalog.saleSetup(shopId),
    who.role === "owner" ? gateways.sales.members(shopId) : Promise.resolve([]),
  ]);
  return { ...who, locations: setup.locations, modes: setup.payment_modes, members };
}

function nameIn(items: readonly { id: string; name: string }[], id: string, what: string) {
  return items.find((item) => item.id === id)?.name ?? `${what} inconnu`;
}

export const modeName = (refs: SaleRefs, id: string) => nameIn(refs.modes, id, "Mode");
export const locationName = (refs: SaleRefs, id: string) => nameIn(refs.locations, id, "Lieu");

export function sellerName(refs: SaleRefs, id: string): string {
  if (id === refs.userId) return "vous";
  return refs.members.find((m) => m.user_id === id)?.name ?? "Vendeur inconnu";
}
