import { useState } from "react";
import { LogOut, Trash2 } from "lucide-react";
import { ConfirmDialog } from "../../shared/ui";

export interface DiscardQueueDialogsProps {
  /** Saisies en attente d'envoi ; 0 = fermé. */
  count: number;
  onCancel: () => void;
  /** Deuxième confirmation donnée : la file est abandonnée, puis la session fermée. */
  onDiscard: () => void;
}

function saisies(count: number): string {
  return count === 1 ? "1 saisie" : `${String(count)} saisies`;
}

/**
 * Déconnexion avec des saisies hors connexion en attente (RG-T24) : **double confirmation**.
 * 1. « N saisies attendent l'envoi » — Retour (conseillé : attendre le réseau) ou continuer ;
 * 2. « Perdre définitivement N saisies ? » — seul ce second « Oui » abandonne la file.
 */
export function DiscardQueueDialogs({ count, onCancel, onDiscard }: DiscardQueueDialogsProps) {
  const [second, setSecond] = useState(false);
  const cancel = () => {
    setSecond(false);
    onCancel();
  };
  return (
    <>
      <ConfirmDialog
        open={count > 0 && !second}
        title={`${saisies(count)} en attente d'envoi`}
        confirmLabel="Se déconnecter quand même"
        confirmIcon={LogOut}
        onCancel={cancel}
        onConfirm={() => {
          setSecond(true);
        }}
      >
        Elles partiront seules au retour du réseau. Si vous vous déconnectez maintenant, elles
        seront perdues.
      </ConfirmDialog>
      <ConfirmDialog
        open={count > 0 && second}
        title={`Perdre définitivement ${saisies(count)} ?`}
        confirmLabel="Oui, perdre les saisies"
        confirmIcon={Trash2}
        onCancel={cancel}
        onConfirm={() => {
          setSecond(false);
          onDiscard();
        }}
      >
        Ces ventes ou dépenses n'arriveront jamais sur le serveur.
      </ConfirmDialog>
    </>
  );
}
