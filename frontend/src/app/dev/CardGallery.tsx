import { ArrowLeftRight, Package, Receipt, ShoppingCart, Truck, Wallet } from "lucide-react";
import {
  ActionTile,
  ActionTileGrid,
  Badge,
  KpiCard,
  ListCard,
  ListCardRow,
  SummaryCard,
} from "../../shared/ui";
import { GallerySection, StateLabel } from "./GallerySection";

const noop = () => undefined;

export function CardGallery() {
  return (
    <>
      <GallerySection title="KpiCard">
        <KpiCard
          label="Ventes du jour"
          amount={2340000}
          detail="3 ventes"
          change={12}
          onOpen={noop}
        />
        <KpiCard label="Argent encaissé du jour" amount={1100000} change={-8} />
        <KpiCard label="Marge du jour" amount={-45000} change={0} />
        <KpiCard label="Valeur du stock" amount={12500000} />
      </GallerySection>

      <GallerySection title="ListCard">
        <ListCard label="Créances">
          <ListCardRow
            title="Moussa Ibrahim"
            subtitle="Vente V-000124 · 10/11/2026"
            amount={600000}
            badge={<Badge status="credit">Crédit</Badge>}
            onOpen={noop}
          />
          <ListCardRow
            title="Aïssatou Bello"
            subtitle="Soldée le 09/11/2026"
            amount={450000}
            badge={<Badge status="success">Soldée</Badge>}
          />
          <ListCardRow
            title="Vente V-000120"
            subtitle="Annulé le 08/11/2026 par Awa — motif : erreur de prix"
            amount={780000}
            badge={<Badge status="danger">Annulée</Badge>}
            cancelled
          />
          <ListCardRow title="Haojue HJ125-8" subtitle="Stock à Garoua : 1" />
        </ListCard>
      </GallerySection>

      <GallerySection title="ActionTile">
        <ActionTileGrid>
          <ActionTile icon={ShoppingCart} label="Nouvelle vente" onClick={noop} />
          <ActionTile icon={Wallet} label="Versement" onClick={noop} />
          <ActionTile icon={Package} label="Stock" onClick={noop} />
          <ActionTile icon={Truck} label="Camions" onClick={noop} />
          <ActionTile icon={ArrowLeftRight} label="Déplacement" onClick={noop} />
          <ActionTile icon={Receipt} label="Dépense" onClick={noop} />
        </ActionTileGrid>
      </GallerySection>

      <GallerySection title="SummaryCard">
        <SummaryCard
          lines={[
            { label: "Total", amount: 800000 },
            { label: "Versé", amount: 200000 },
          ]}
          due={600000}
        />
        <StateLabel>Soldé</StateLabel>
        <SummaryCard lines={[{ label: "Total", amount: 450000 }]} due={0} />
      </GallerySection>

      <GallerySection title="Badge">
        <div className="flex flex-wrap gap-2">
          <Badge status="credit">Crédit</Badge>
          <Badge status="success">Soldée</Badge>
          <Badge status="warning">Stock bas</Badge>
          <Badge status="danger">Annulée</Badge>
          <Badge status="offline">Hors connexion</Badge>
        </div>
      </GallerySection>
    </>
  );
}
