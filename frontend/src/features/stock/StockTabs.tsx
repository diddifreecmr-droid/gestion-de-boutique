import { Package, Tags } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";
import { catalogListPath } from "../catalog/catalogPaths";
import { stockMatrixPath } from "./stockNav";

export type StockTab = "stock" | "articles";

/** Classes des onglets : tokens seulement ; l'onglet actif se lit aussi sans la couleur (P7). */
function tabClasses(active: boolean): string {
  const state = active
    ? "border-primary bg-primary-soft ring-1 ring-inset ring-primary"
    : "border-border-strong bg-surface hover:bg-primary-soft";
  return (
    "flex min-h-(--control-md) items-center justify-center gap-2 rounded-md border px-4 " +
    "text-label font-semibold text-primary no-underline transition-colors " +
    "duration-(--duration-fast) ease-out outline-hidden focus-visible:outline-2 " +
    `focus-visible:outline-solid focus-visible:outline-offset-3 focus-visible:outline-primary ${state}`
  );
}

function Tab(props: { href: string; icon: LucideIcon; label: string; active: boolean }) {
  const { href, icon: Icon, label, active } = props;
  return (
    <li>
      <Link to={href} aria-current={active ? "page" : undefined} className={tabClasses(active)}>
        <Icon aria-hidden="true" className="size-6 shrink-0" />
        <span>{label}</span>
      </Link>
    </li>
  );
}

/**
 * Onglets de la section « Stock » du propriétaire et du comptable : la matrice (« Stock ») et
 * la gestion des articles (« Articles », module catalogue). Le vendeur n'a pas d'onglets.
 */
export function StockTabs({ shopId, active }: { shopId: string; active: StockTab }) {
  return (
    <nav aria-label="Section Stock">
      <ul className="m-0 grid list-none grid-cols-2 gap-2 p-0">
        <Tab
          href={stockMatrixPath(shopId)}
          icon={Package}
          label="Stock"
          active={active === "stock"}
        />
        <Tab
          href={catalogListPath(shopId)}
          icon={Tags}
          label="Articles"
          active={active === "articles"}
        />
      </ul>
    </nav>
  );
}
