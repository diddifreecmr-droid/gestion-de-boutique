import { ListCard, ListCardRow } from "../../shared/ui";
import { VIEW, type SettingsView } from "./settingsNav";

export interface SettingsHubProps {
  title: string;
  onOpen: (view: SettingsView) => void;
}

const ENTRIES: readonly { view: SettingsView; title: string; subtitle: string }[] = [
  {
    view: VIEW.members,
    title: "Membres",
    subtitle: "Ajouter un vendeur, un comptable, un chauffeur ; rôle, code, accès",
  },
  { view: VIEW.locations, title: "Lieux", subtitle: "Boutiques et entrepôts, points de vente" },
  {
    view: VIEW.paymentModes,
    title: "Modes de paiement",
    subtitle: "Espèces, Orange Money, MTN MoMo… et la référence demandée",
  },
  {
    view: VIEW.shop,
    title: "Réglages de la boutique",
    subtitle: "Prix minimum, seuil de stock, reçu et en-tête",
  },
];

/**
 * Sommaire des Réglages (propriétaire) : une entrée par écran. « Mon compte » n'y est pas : son
 * seul accès est le bouton « Compte » de la barre du haut (audit UX du 13/11/2026).
 */
export function SettingsHub({ title, onOpen }: SettingsHubProps) {
  return (
    <div className="flex flex-col gap-5">
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <ListCard label="Réglages de la boutique">
        {ENTRIES.map((entry) => (
          <ListCardRow
            key={entry.view}
            title={entry.title}
            subtitle={entry.subtitle}
            onOpen={() => {
              onOpen(entry.view);
            }}
          />
        ))}
      </ListCard>
    </div>
  );
}
