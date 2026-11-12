/**
 * PROVISOIRE (T12) — profil « Motos et camions » écrit en dur, en attendant
 * `GET /shops/{id}/profile` (T10 / T12bis). Les menus recopient le CDC § 17.4 mot pour mot.
 */
import {
  ArrowLeftRight,
  Banknote,
  ClipboardList,
  CirclePlus,
  Ellipsis,
  HandCoins,
  House,
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
import type { Role } from "../auth/me";
import { HOME_KEY, MORE_KEY, type MenuEntry, type ShopProfile } from "./types";

const HOME: MenuEntry = { key: HOME_KEY, label: "Accueil", icon: House };
const STOCK: MenuEntry = { key: "stock", label: "Stock", icon: Package };
const PURCHASES: MenuEntry = {
  key: "achats",
  label: "Achats",
  icon: ShoppingCart,
  module: "purchases",
};
const RECEIVABLES: MenuEntry = {
  key: "creances",
  label: "Créances",
  icon: HandCoins,
  module: "receivables",
};
const EXPENSES: MenuEntry = {
  key: "depenses",
  label: "Dépenses",
  icon: Wallet,
  module: "expenses",
};

const MENUS: Readonly<Record<Role, readonly MenuEntry[]>> = {
  owner: [
    HOME,
    { key: "ventes", label: "Ventes", icon: ReceiptText },
    STOCK,
    { key: "camions", label: "Camions", icon: Truck, module: "transport" },
    { key: MORE_KEY, label: "Plus", icon: Ellipsis },
  ],
  seller: [
    HOME,
    { key: "nouvelle-vente", label: "Nouvelle vente", icon: CirclePlus },
    { key: "mes-ventes", label: "Mes ventes", icon: ReceiptText },
    RECEIVABLES,
    STOCK,
  ],
  accountant: [
    HOME,
    PURCHASES,
    STOCK,
    { key: "deplacements", label: "Déplacements", icon: ArrowLeftRight, module: "transfers" },
    EXPENSES,
  ],
  // Le chauffeur arrive sur « Mon voyage » : c'est son accueil.
  driver: [
    { key: HOME_KEY, label: "Mon voyage", icon: Route },
    { key: "mes-depenses", label: "Mes dépenses", icon: Wallet, module: "transport" },
    { key: "mes-voyages", label: "Mes voyages", icon: ClipboardList, module: "transport" },
  ],
};

const OWNER_MORE: readonly MenuEntry[] = [
  RECEIVABLES,
  PURCHASES,
  EXPENSES,
  { key: "clients", label: "Clients", icon: Users },
  { key: "paie", label: "Paie", icon: Banknote, module: "transport" },
  { key: "journal", label: "Journal", icon: ScrollText },
  { key: "reglages", label: "Réglages", icon: Settings },
];

const ROLE_LABELS: Readonly<Record<Role, string>> = {
  owner: "Propriétaire",
  seller: "Vendeur",
  accountant: "Comptable",
  driver: "Chauffeur",
};

export const MOTOS_PROFILE: ShopProfile = {
  code: "motos",
  provisional: true,
  roleLabel: (role) => ROLE_LABELS[role],
  menu: (role) => MENUS[role],
  more: (role) => (role === "owner" ? OWNER_MORE : []),
};
