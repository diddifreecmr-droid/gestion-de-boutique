import { Ban, KeyRound, LockOpen, LogOut, RotateCcw, UserCog } from "lucide-react";
import type { ShopMember } from "../../../core/gateways/shopAdminContract";
import { Button } from "../../../shared/ui";

/** Action qui demande une confirmation (ou, pour « unlock », s'exécute directement). */
export type MemberAskKind = "deactivate" | "reset-pin" | "revoke-devices" | "unlock";

export interface MemberAsk {
  kind: MemberAskKind;
  member: ShopMember;
}

/** Raison affichée sous les actions indisponibles sur son propre compte (RG-D08). */
export const SELF_LOCKED = "Votre propre accès se gère depuis « Mon compte »";

export interface MemberActionsProps {
  member: ShopMember;
  isSelf: boolean;
  busy: boolean;
  onEditRole: () => void;
  onReactivate: () => void;
  onAsk: (ask: MemberAsk) => void;
}

/**
 * Actions sur un membre (UC-SOC-04, décision du 11/11/2026) : rôle et désactivation visent
 * le rattachement à **cette** boutique ; débloquer, redonner un code et déconnecter les
 * appareils agissent sur le compte entier.
 */
export function MemberActions({
  member,
  isSelf,
  busy,
  onEditRole,
  onReactivate,
  onAsk,
}: MemberActionsProps) {
  const self = isSelf ? { disabledReason: SELF_LOCKED } : {};
  const ask = (kind: MemberAskKind) => () => {
    onAsk({ kind, member });
  };
  return (
    <div className="flex flex-wrap gap-2">
      <Button variant="secondary" icon={UserCog} onClick={onEditRole} {...self}>
        Changer le rôle
      </Button>
      {member.locked && (
        <Button variant="secondary" icon={LockOpen} loading={busy} onClick={ask("unlock")}>
          Débloquer
        </Button>
      )}
      <Button variant="secondary" icon={KeyRound} onClick={ask("reset-pin")} {...self}>
        Redonner un code
      </Button>
      <Button variant="secondary" icon={LogOut} onClick={ask("revoke-devices")} {...self}>
        Déconnecter ses appareils
      </Button>
      {member.active ? (
        <Button variant="secondary" icon={Ban} onClick={ask("deactivate")} {...self}>
          Désactiver
        </Button>
      ) : (
        <Button variant="secondary" icon={RotateCcw} loading={busy} onClick={onReactivate}>
          Réactiver
        </Button>
      )}
    </div>
  );
}
