import { Ban, KeyRound, LogOut } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ConfirmDialog } from "../../../shared/ui";
import type { MemberAsk, MemberAskKind } from "./MemberActions";

type Confirmed = Exclude<MemberAskKind, "unlock">;

const TEXTS: Readonly<
  Record<
    Confirmed,
    {
      title: (name: string) => string;
      label: string;
      icon: LucideIcon;
      body: (name: string) => string;
    }
  >
> = {
  deactivate: {
    title: (name) => `Désactiver ${name} ?`,
    label: "Désactiver",
    icon: Ban,
    body: (name) =>
      `${name} n'aura plus accès à cette boutique. Son historique reste ; vous pourrez le réactiver.`,
  },
  "reset-pin": {
    title: (name) => `Redonner un code à ${name} ?`,
    label: "Redonner un code",
    icon: KeyRound,
    body: (name) =>
      `Son code actuel ne marchera plus. Un code provisoire s'affichera une seule fois ; ${name} devra le changer à sa prochaine connexion. Le compte est aussi débloqué.`,
  },
  "revoke-devices": {
    title: (name) => `Déconnecter les appareils de ${name} ?`,
    label: "Déconnecter",
    icon: LogOut,
    body: (name) =>
      `Tous les téléphones de ${name} sont déconnectés, dans toutes ses boutiques. Il devra se reconnecter avec son code.`,
  },
};

export interface MemberConfirmProps {
  ask: MemberAsk | null;
  onConfirm: (ask: MemberAsk) => void;
  onCancel: () => void;
}

/** Confirmation des actions sensibles sur un membre (§ 6.5) ; « Débloquer » n'en a pas. */
export function MemberConfirm({ ask, onConfirm, onCancel }: MemberConfirmProps) {
  if (ask === null || ask.kind === "unlock") return null;
  const text = TEXTS[ask.kind];
  const name = ask.member.name;
  return (
    <ConfirmDialog
      open
      title={text.title(name)}
      confirmLabel={text.label}
      confirmIcon={text.icon}
      onCancel={onCancel}
      onConfirm={() => {
        onConfirm(ask);
      }}
    >
      {text.body(name)}
    </ConfirmDialog>
  );
}
