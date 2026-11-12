import { useState } from "react";
import type { MemberPatch, ShopMember } from "../../../core/gateways/shopAdminContract";
import { useShopAdmin } from "../../../core/gateways/httpShopAdmin";
import { useSignedIn } from "../../../core/services/servicesContext";
import { useToast } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { useLoad } from "../../expenses/useLoad";
import { ScreenFrame } from "../ScreenFrame";
import type { SettingsScreenProps } from "../settingsNav";
import { useAction } from "../useAction";
import { AddMemberForm } from "./AddMemberForm";
import type { MemberAsk } from "./MemberActions";
import { MemberConfirm } from "./MemberConfirm";
import { loadMemberRefs } from "./memberRefs";
import { MemberRow } from "./MemberRow";
import { TemporaryPinNotice } from "./TemporaryPinNotice";

const plural = (count: number, word: string) => `${String(count)} ${word}${count > 1 ? "s" : ""}`;

/**
 * Membres de la boutique (UC-SOC-04, MEM-01 à 04) : ajouter un vendeur, un comptable, un
 * chauffeur ; changer le rôle ; désactiver ; débloquer ; redonner un code ; déconnecter.
 */
export function MembersScreen({ shopId, onBack }: SettingsScreenProps) {
  const gateway = useShopAdmin();
  const me = useSignedIn();
  const toast = useToast();
  const [round, setRound] = useState(0);
  const loaded = useLoad(`${shopId}:${String(round)}`, () => loadMemberRefs(gateway, shopId));
  const [changed, setChanged] = useState<ShopMember[]>([]);
  const [pin, setPin] = useState<{ name: string; pin: string } | null>(null);
  const [ask, setAsk] = useState<MemberAsk | null>(null);
  const action = useAction();

  const keep = (member: ShopMember) => {
    setChanged((current) => [...current.filter((m) => m.user_id !== member.user_id), member]);
  };
  const patch = (member: ShopMember, change: Omit<MemberPatch, "version">) =>
    action.run(member.user_id, async () => {
      keep(
        await gateway.updateMember(shopId, member.user_id, { ...change, version: member.version }),
      );
    });
  const execute = ({ kind, member }: MemberAsk) => {
    setAsk(null);
    const id = member.user_id;
    void action.run(id, async () => {
      if (kind === "deactivate") {
        keep(await gateway.updateMember(shopId, id, { active: false, version: member.version }));
      } else if (kind === "unlock") {
        await gateway.unlock(shopId, id);
        keep({ ...member, locked: false });
        toast.show({ tone: "success", message: `${member.name} est débloqué.` });
      } else if (kind === "reset-pin") {
        const temporary = await gateway.resetPin(shopId, id);
        keep({ ...member, locked: false, must_change_pin: true });
        setPin({ name: member.name, pin: temporary });
      } else {
        const count = await gateway.revokeDevices(shopId, id);
        const devices = `${plural(count, "appareil")} ${count > 1 ? "déconnectés" : "déconnecté"}`;
        toast.show({ tone: "success", message: `${member.name} : ${devices}.` });
      }
    });
  };

  return (
    <ScreenFrame
      title="Membres"
      onBack={onBack}
      loaded={loaded}
      onRetry={() => {
        setRound((n) => n + 1);
      }}
    >
      {(refs) => {
        const byId = new Map(refs.members.map((member) => [member.user_id, member]));
        for (const member of changed) byId.set(member.user_id, member);
        const members = [...byId.values()].sort((a, b) => a.name.localeCompare(b.name, "fr"));
        return (
          <>
            {pin !== null && (
              <TemporaryPinNotice
                name={pin.name}
                pin={pin.pin}
                onDone={() => {
                  setPin(null);
                }}
              />
            )}
            <ul
              aria-label="Membres de la boutique"
              className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card"
            >
              {members.map((member) => (
                <MemberRow
                  key={member.user_id}
                  member={member}
                  refs={refs}
                  isSelf={member.user_id === me.userId}
                  busy={action.busy === member.user_id}
                  onPatch={(change) => patch(member, change)}
                  onAsk={(next) => {
                    if (next.kind === "unlock") execute(next);
                    else setAsk(next);
                  }}
                />
              ))}
            </ul>
            {action.message !== null && <FormMessage text={action.message} />}
            <AddMemberForm
              shopId={shopId}
              refs={refs}
              onAdded={(created) => {
                keep(created.member);
                if (created.temporary_pin !== null) {
                  setPin({ name: created.member.name, pin: created.temporary_pin });
                } else {
                  toast.show({
                    tone: "success",
                    message: `${created.member.name} avait déjà un compte : il garde son code.`,
                  });
                }
              }}
            />
            <MemberConfirm
              ask={ask}
              onConfirm={execute}
              onCancel={() => {
                setAsk(null);
              }}
            />
          </>
        );
      }}
    </ScreenFrame>
  );
}
