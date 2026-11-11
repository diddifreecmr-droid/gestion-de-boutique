import { createContext, useContext } from "react";

/** Durée d'affichage d'un toast de succès (§ 6.5). Les erreurs restent jusqu'à fermeture. */
export const TOAST_SUCCESS_MS = 4000;

export type ToastTone = "success" | "error";

export interface ToastMessage {
  tone: ToastTone;
  /** « Vente enregistrée — reçu n° V-000124 ». */
  message: string;
}

export interface ToastApi {
  /** Affiche un toast et renvoie son identifiant (pour le fermer par code). */
  show: (toast: ToastMessage) => number;
  dismiss: (id: number) => void;
}

export const ToastContext = createContext<ToastApi | null>(null);

/** Accès aux toasts ; hors d'un ToastProvider, c'est une erreur de câblage (fail-fast). */
export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (api === null) {
    throw new Error("useToast doit être appelé sous un <ToastProvider>");
  }
  return api;
}
