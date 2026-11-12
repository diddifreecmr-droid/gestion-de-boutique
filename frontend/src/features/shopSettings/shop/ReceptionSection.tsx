import { useState } from "react";
import type { ShopLocation } from "../../../core/gateways/shopAdminContract";
import { ChoiceChips } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { SettingsSection, type SectionProps } from "./SettingsSection";

/**
 * Lieu de réception des achats par défaut (décision Q-01, specs § 15.1) : un lieu actif de la
 * boutique, proposé à la saisie d'un achat.
 */
export function ReceptionSection(props: SectionProps & { locations: readonly ShopLocation[] }) {
  const { settings, locations } = props;
  const active = locations.filter((location) => location.active);
  const known = active.some((location) => location.id === settings.reception_location_id);
  const [chosen, setChosen] = useState<string | null>(
    known ? settings.reception_location_id : null,
  );
  const [error, setError] = useState<string | null>(null);

  const collect = () => {
    if (chosen === null) {
      setError("Choisissez le lieu de réception");
      return null;
    }
    setError(null);
    return { reception_location_id: chosen };
  };

  return (
    <SettingsSection {...props} title="Réception des achats" collect={collect}>
      {active.length === 0 ? (
        <FormMessage text="Aucun lieu actif : ajoutez-en un dans « Lieux »." />
      ) : (
        <ChoiceChips
          label="Lieu de réception par défaut"
          options={active.map((location) => ({ value: location.id, label: location.name }))}
          value={chosen}
          onChange={(value) => {
            setChosen(value);
            setError(null);
          }}
        />
      )}
      {error !== null && <FormMessage text={error} />}
    </SettingsSection>
  );
}
