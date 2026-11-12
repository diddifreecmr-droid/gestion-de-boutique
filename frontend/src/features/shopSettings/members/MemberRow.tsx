import { useState } from "react";
import { Check } from "lucide-react";
import { parseRole } from "../../../core/auth/me";
import type { MemberPatch, ShopMember } from "../../../core/gateways/shopAdminContract";
import { Badge, Button } from "../../../shared/ui";
import { MemberActions, type MemberAsk } from "./MemberActions";
import { locationName, roleLabel, type MemberRefs } from "./memberRefs";
import { roleDraftError, type RoleDraft } from "./roleDraft";
import { RoleFields } from "./RoleFields";

export interface MemberRowProps {
  member: ShopMember;
  refs: MemberRefs;
  /** Le propriétaire connecté : ses propres accès ne se coupent pas d'ici. */
  isSelf: boolean;
  busy: boolean;
  onPatch: (patch: Omit<MemberPatch, "version">) => Promise<boolean>;
  onAsk: (ask: MemberAsk) => void;
}

/** Un membre : rôle, lieu habituel, état du compte, puis ses actions. */
export function MemberRow({ member, refs, isSelf, busy, onPatch, onAsk }: MemberRowProps) {
  const [draft, setDraft] = useState<RoleDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const place = locationName(refs, member.default_location_id);

  const save = async () => {
    if (draft === null) return;
    const problem = roleDraftError(refs, draft);
    setError(problem);
    if (problem !== null) return;
    const done = await onPatch({
      role: draft.role,
      default_location_id: draft.role === "seller" ? draft.locationId : null,
    });
    if (done) setDraft(null);
  };

  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <span className="flex flex-wrap items-center gap-2">
        <span className={`text-lead ${member.active ? "text-text" : "text-text-muted"}`}>
          {member.name}
        </span>
        {isSelf && <Badge status="success">Vous</Badge>}
        {!member.active && <Badge status="danger">Désactivé</Badge>}
        {member.locked && <Badge status="warning">Bloqué</Badge>}
        {member.must_change_pin && <Badge status="offline">Code provisoire</Badge>}
      </span>
      <span className="text-body text-text-muted">
        {roleLabel(refs, member.role)}
        {place !== null && ` · ${place}`} · {member.phone}
      </span>
      {draft !== null ? (
        <div className="flex flex-col gap-4">
          <RoleFields
            prefix={`Changer le rôle de ${member.name}`}
            refs={refs}
            draft={draft}
            error={error}
            onChange={(next) => {
              setDraft(next);
              setError(null);
            }}
          />
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              fullWidth
              onClick={() => {
                setDraft(null);
              }}
            >
              Retour
            </Button>
            <Button
              variant="secondary"
              icon={Check}
              fullWidth
              loading={busy}
              onClick={() => void save()}
            >
              Enregistrer
            </Button>
          </div>
        </div>
      ) : (
        <MemberActions
          member={member}
          isSelf={isSelf}
          busy={busy}
          onEditRole={() => {
            setDraft({ role: parseRole(member.role), locationId: member.default_location_id });
          }}
          onReactivate={() => void onPatch({ active: true })}
          onAsk={onAsk}
        />
      )}
    </li>
  );
}
