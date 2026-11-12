import { ChoiceChips } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { salePoints, type MemberRefs } from "./memberRefs";
import type { RoleDraft } from "./roleDraft";

export interface RoleFieldsProps {
  prefix: string;
  refs: MemberRefs;
  draft: RoleDraft;
  /** Erreur du lieu, affichée seulement après un essai d'envoi. */
  error: string | null;
  onChange: (draft: RoleDraft) => void;
}

/** Choix du rôle (proposé par le profil) puis, pour un vendeur, du point de vente habituel. */
export function RoleFields({ prefix, refs, draft, error, onChange }: RoleFieldsProps) {
  const points = salePoints(refs);
  return (
    <>
      <ChoiceChips
        label={`${prefix} — rôle`}
        options={refs.roles}
        value={draft.role}
        onChange={(role) => {
          const only = points.length === 1 ? (points[0]?.id ?? null) : null;
          onChange({ role, locationId: role === "seller" ? (draft.locationId ?? only) : null });
        }}
      />
      {draft.role === "seller" && points.length > 0 && (
        <ChoiceChips
          label={`${prefix} — lieu de vente habituel`}
          options={points.map((point) => ({ value: point.id, label: point.name }))}
          value={points.some((point) => point.id === draft.locationId) ? draft.locationId : null}
          onChange={(locationId) => {
            onChange({ ...draft, locationId });
          }}
        />
      )}
      {error !== null && <FormMessage text={error} />}
    </>
  );
}
