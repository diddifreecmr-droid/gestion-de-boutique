import type { MouseEvent } from "react";
import { Check, House, MoreHorizontal, Package, ShoppingCart, Truck } from "lucide-react";
import { ActionBar, BottomNav, Button, TopBar, type NavItem } from "../../shared/ui";
import { formatMoney } from "../../shared/format";
import { GallerySection, StateLabel } from "./GallerySection";

const noop = () => undefined;

const NAV_ITEMS: NavItem[] = [
  { key: "home", label: "Accueil", icon: House, href: "#accueil" },
  { key: "sales", label: "Ventes", icon: ShoppingCart, href: "#ventes" },
  { key: "stock", label: "Stock", icon: Package, href: "#stock" },
  { key: "trucks", label: "Camions", icon: Truck, href: "#camions" },
  { key: "more", label: "Plus", icon: MoreHorizontal, href: "#plus" },
];

/** La vitrine ne navigue pas : le lien est intercepté comme le ferait le routeur. */
const stay = (_item: NavItem, event: MouseEvent<HTMLAnchorElement>) => {
  event.preventDefault();
};

export function NavigationGallery() {
  return (
    <>
      <GallerySection title="TopBar">
        <TopBar title="Motos Garoua" onTitleClick={noop} alertCount={3} onAlertsClick={noop} />
        <StateLabel>Écran de détail, aucune alerte</StateLabel>
        <TopBar title="Nouvelle vente" onBack={noop} alertCount={0} onAlertsClick={noop} />
        <StateLabel>Une seule boutique, plus de 99 alertes</StateLabel>
        <TopBar title="Tissus Maroua" alertCount={120} onAlertsClick={noop} />
      </GallerySection>

      <GallerySection title="BottomNav">
        <BottomNav
          items={NAV_ITEMS}
          activeKey="home"
          fixed={false}
          label="Exemple de navigation (5 entrées)"
          onNavigate={stay}
        />
        <StateLabel>Droits réduits (3 entrées)</StateLabel>
        <BottomNav
          items={NAV_ITEMS.slice(1, 4)}
          activeKey="stock"
          fixed={false}
          label="Exemple de navigation (3 entrées)"
          onNavigate={stay}
        />
      </GallerySection>

      <GallerySection title="ActionBar">
        <ActionBar
          fixed={false}
          summary={
            <span className="flex justify-between gap-4">
              <span>Total</span>
              <span className="font-bold tabular-nums">{formatMoney(780000)}</span>
            </span>
          }
        >
          <Button size="lg" fullWidth icon={Check}>
            Valider la vente
          </Button>
        </ActionBar>
      </GallerySection>
    </>
  );
}
