import { useState } from "react";
import { Switch, TextField } from "../../../shared/ui";
import { SettingsSection, type SectionProps } from "./SettingsSection";
import { parseOptionalInt } from "./settingsInputs";

/** Aide de l'interrupteur (décision client QC-4 du 13/11/2026, specs § 15.1). */
export const EMPLOYEE_EXCHANGE_HINT =
  "Désactivé (par défaut) : vous seul faites les échanges. Activé : l'employé échange ses propres ventes, dans le délai.";

export const EXCHANGE_DAYS_HINT =
  "Compté depuis le jour de la vente (7 : jusqu'au 7e jour après). Vide : sans limite. Vous pouvez toujours le dépasser : l'échange est alors inscrit au journal.";

/**
 * Échanges (UC-PAP-01, QC-4) : délai d'échange `exchange_days` (0 à 365 jours, vide = sans
 * limite) et autorisation de l'employé `employee_exchange_allowed` (désactivée par défaut).
 */
export function ExchangeSettingsSection(props: SectionProps) {
  const { settings } = props;
  const [days, setDays] = useState(
    settings.exchange_days === null ? "" : String(settings.exchange_days),
  );
  const [employee, setEmployee] = useState(settings.employee_exchange_allowed);
  const [error, setError] = useState<string | undefined>(undefined);

  const collect = () => {
    const parsed = parseOptionalInt(days, 0, 365);
    setError(parsed.ok ? undefined : parsed.error);
    if (!parsed.ok) return null;
    return { exchange_days: parsed.value, employee_exchange_allowed: employee };
  };

  return (
    <SettingsSection {...props} title="Échanges" collect={collect}>
      <TextField
        label="Délai d'échange (jours, facultatif)"
        hint={EXCHANGE_DAYS_HINT}
        inputMode="numeric"
        value={days}
        error={error}
        onChange={(event) => {
          setDays(event.target.value);
          setError(undefined);
        }}
      />
      <Switch
        label="L'employé peut faire des échanges"
        hint={EMPLOYEE_EXCHANGE_HINT}
        checked={employee}
        onChange={setEmployee}
      />
    </SettingsSection>
  );
}
