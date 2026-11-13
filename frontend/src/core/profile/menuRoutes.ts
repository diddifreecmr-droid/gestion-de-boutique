/**
 * Codes de menu servis par `GET /shops/{id}/profile` (backend `domain/profiles/*.py`) → segment
 * d'URL et icône côté client. Le code est stable ; le libellé vient du serveur. Un code absent
 * d'ici est une rupture de contrat : erreur explicite (fail-fast), jamais une entrée devinée.
 */
import {
  ArrowLeftRight,
  Banknote,
  ClipboardCheck,
  ClipboardList,
  CirclePlus,
  Ellipsis,
  FileSpreadsheet,
  HandCoins,
  House,
  type LucideIcon,
  Package,
  ReceiptText,
  Route,
  ScrollText,
  Settings,
  ShoppingCart,
  Truck,
  Users,
  Wallet,
} from "lucide-react";
import { HOME_KEY, MORE_KEY } from "./types";

export interface MenuRoute {
  /** Segment d'URL : `/s/{shopId}/{key}` (l'accueil a la clé `""`). */
  key: string;
  icon: LucideIcon;
}

/** Section « Inventaire » (menu du comptable Prêt-à-porter et Textile, CDC § 18.5). */
export const INVENTORY_KEY = "inventaire";

const ROUTES: Readonly<Record<string, MenuRoute>> = {
  home: { key: HOME_KEY, icon: House },
  more: { key: MORE_KEY, icon: Ellipsis },
  sales: { key: "ventes", icon: ReceiptText },
  new_sale: { key: "nouvelle-vente", icon: CirclePlus },
  my_sales: { key: "mes-ventes", icon: ReceiptText },
  stock: { key: "stock", icon: Package },
  inventory: { key: INVENTORY_KEY, icon: ClipboardCheck },
  receivables: { key: "creances", icon: HandCoins },
  purchases: { key: "achats", icon: ShoppingCart },
  expenses: { key: "depenses", icon: Wallet },
  customers: { key: "clients", icon: Users },
  audit: { key: "journal", icon: ScrollText },
  import: { key: "import", icon: FileSpreadsheet },
  settings: { key: "reglages", icon: Settings },
  trucks: { key: "camions", icon: Truck },
  payroll: { key: "paie", icon: Banknote },
  transfers: { key: "deplacements", icon: ArrowLeftRight },
  // Le chauffeur arrive sur « Mon voyage » : c'est son accueil.
  my_trip: { key: HOME_KEY, icon: Route },
  my_trip_expenses: { key: "mes-depenses", icon: Wallet },
  my_trips: { key: "mes-voyages", icon: ClipboardList },
};

export const MENU_CODES: readonly string[] = Object.keys(ROUTES);

export function menuRoute(code: string): MenuRoute {
  const found = Object.hasOwn(ROUTES, code) ? ROUTES[code] : undefined;
  if (found === undefined) {
    throw new Error(
      `Code de menu inconnu reçu de l'API : « ${code} » (attendu ${MENU_CODES.join(", ")})`,
    );
  }
  return found;
}
