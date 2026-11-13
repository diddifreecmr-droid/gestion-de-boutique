import { AlertTriangle } from "lucide-react";
import { useModules } from "../../../core/profile/modulesContext";
import { ChoiceChips, TextField } from "../../../shared/ui";
import { YesNoChips } from "../YesNoChips";
import { KIND_OPTIONS, type LocationDraft } from "./locationDraft";

export interface LocationFieldsProps {
  /** Préfixe des libellés, pour distinguer plusieurs formulaires à l'écran. */
  prefix: string;
  draft: LocationDraft;
  nameError: string | undefined;
  onChange: (draft: LocationDraft) => void;
}

/** Avertissement d'entrepôt tant que les déplacements entre lieux n'existent pas (QC-5). */
export const WAREHOUSE_WARNING =
  "Déplacement disponible plus tard : la marchandise d'un entrepôt ne peut pas encore revenir en boutique. Les achats restent reçus au lieu de réception (Réglages de la boutique).";

/**
 * Champs d'un lieu (UC-SOC-05) : nom unique, type, point de vente, ville. Choisir « Entrepôt »
 * sans le module Transferts affiche l'avertissement avant l'envoi (QC-5).
 */
export function LocationFields({ prefix, draft, nameError, onChange }: LocationFieldsProps) {
  const transfers = useModules().has("transfers");
  return (
    <>
      <TextField
        label={`${prefix} — nom`}
        value={draft.name}
        maxLength={200}
        error={nameError}
        onChange={(event) => {
          onChange({ ...draft, name: event.target.value });
        }}
      />
      <ChoiceChips
        label={`${prefix} — type`}
        options={KIND_OPTIONS}
        value={draft.kind}
        onChange={(kind) => {
          onChange({ ...draft, kind });
        }}
      />
      {draft.kind === "warehouse" && !transfers && (
        <p role="status" className="m-0 flex items-start gap-2 text-body text-warning-text">
          <AlertTriangle aria-hidden="true" className="size-6 shrink-0" />
          <span>{WAREHOUSE_WARNING}</span>
        </p>
      )}
      <YesNoChips
        label={`${prefix} — point de vente`}
        value={draft.isPointOfSale}
        onChange={(isPointOfSale) => {
          onChange({ ...draft, isPointOfSale });
        }}
      />
      <TextField
        label={`${prefix} — ville (facultatif)`}
        value={draft.city}
        maxLength={200}
        onChange={(event) => {
          onChange({ ...draft, city: event.target.value });
        }}
      />
    </>
  );
}
