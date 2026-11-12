/**
 * Navigation des Réglages de la boutique (UC-SOC-04 à 06) : la vue est dans l'adresse
 * (`?vue=membres`), le bouton retour du téléphone revient donc à l'écran précédent.
 */

/** Clé de section du menu « Plus » du propriétaire (profil, CDC § 17.4). */
export const SETTINGS_KEY = "reglages";

export const VIEW = {
  members: "membres",
  locations: "lieux",
  paymentModes: "modes",
  shop: "boutique",
} as const;

export type SettingsView = (typeof VIEW)[keyof typeof VIEW];

/** Commun aux écrans des réglages : boutique active et retour au sommaire. */
export interface SettingsScreenProps {
  shopId: string;
  onBack: () => void;
}
