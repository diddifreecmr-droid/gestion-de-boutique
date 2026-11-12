import { useState } from "react";
import { UserPlus } from "lucide-react";
import type { MemberCreated } from "../../../core/gateways/shopAdminContract";
import { useShopAdmin } from "../../../core/gateways/httpShopAdmin";
import { Button, TextField } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { useAction } from "../useAction";
import { salePoints, type MemberRefs } from "./memberRefs";
import { roleDraftError, type RoleDraft } from "./roleDraft";
import { RoleFields } from "./RoleFields";

export interface AddMemberFormProps {
  shopId: string;
  refs: MemberRefs;
  onAdded: (created: MemberCreated) => void;
}

const PREFIX = "Nouveau membre";

interface FormErrors {
  name?: string | undefined;
  phone?: string | undefined;
  role?: string | undefined;
}

/** Vendeur proposé d'abord (cas le plus courant), sinon le premier rôle du profil. */
function firstDraft(refs: MemberRefs): RoleDraft {
  const first = refs.roles.find((choice) => choice.value === "seller") ?? refs.roles[0];
  if (first === undefined) throw new Error("Aucun rôle à proposer (profil vide)");
  const points = salePoints(refs);
  const only = first.value === "seller" && points.length === 1 ? (points[0]?.id ?? null) : null;
  return { role: first.value, locationId: only };
}

/**
 * Ajouter un membre (UC-SOC-04, MEM-01) : nom, téléphone, rôle et, pour un vendeur, son point
 * de vente. Un téléphone déjà connu rattache le compte existant (son nom et son code restent).
 */
export function AddMemberForm({ shopId, refs, onAdded }: AddMemberFormProps) {
  const gateway = useShopAdmin();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [draft, setDraft] = useState<RoleDraft>(() => firstDraft(refs));
  const [errors, setErrors] = useState<FormErrors>({});
  const action = useAction();

  const submit = async () => {
    const found: FormErrors = {
      name: name.trim() === "" ? "Le nom est vide" : undefined,
      phone: phone.trim() === "" ? "Le téléphone est vide" : undefined,
      role: roleDraftError(refs, draft) ?? undefined,
    };
    setErrors(found);
    if (Object.values(found).some((value) => value !== undefined)) return;
    const done = await action.run("add", async () => {
      onAdded(
        await gateway.addMember(shopId, {
          name: name.trim(),
          phone: phone.trim(),
          role: draft.role,
          default_location_id: draft.role === "seller" ? draft.locationId : null,
        }),
      );
    });
    if (done) {
      setName("");
      setPhone("");
    }
  };

  return (
    <section aria-labelledby="new-member" className="flex flex-col gap-4">
      <h2 id="new-member" className="m-0 text-title-sm font-semibold text-text">
        Ajouter un membre
      </h2>
      <TextField
        label={`${PREFIX} — nom`}
        value={name}
        maxLength={120}
        autoComplete="off"
        error={errors.name}
        onChange={(event) => {
          setName(event.target.value);
          setErrors((current) => ({ ...current, name: undefined }));
        }}
      />
      <TextField
        label={`${PREFIX} — téléphone`}
        hint="Il se connecte avec ce numéro"
        type="tel"
        inputMode="tel"
        value={phone}
        maxLength={32}
        autoComplete="off"
        error={errors.phone}
        onChange={(event) => {
          setPhone(event.target.value);
          setErrors((current) => ({ ...current, phone: undefined }));
        }}
      />
      <RoleFields
        prefix={PREFIX}
        refs={refs}
        draft={draft}
        error={errors.role ?? null}
        onChange={(next) => {
          setDraft(next);
          setErrors((current) => ({ ...current, role: undefined }));
        }}
      />
      {action.message !== null && <FormMessage text={action.message} />}
      <Button
        variant="secondary"
        icon={UserPlus}
        fullWidth
        loading={action.busy === "add"}
        onClick={() => void submit()}
      >
        Ajouter le membre
      </Button>
    </section>
  );
}
