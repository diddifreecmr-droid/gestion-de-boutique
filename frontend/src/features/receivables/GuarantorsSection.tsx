import { useId, useState } from "react";
import { IdCard, UserPlus } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { Receivable } from "../../core/gateways/receivablesContract";
import { Button, TextField } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { normalizePhone, PHONE_HINT } from "../sales/phone";
import { useAction } from "./useAction";

/** Raison affichée sous « Pièce d'identité » : les pièces jointes arrivent ensuite. */
export const ATTACHMENTS_PENDING = "Pièces jointes : à venir";

export interface GuarantorsSectionProps {
  shopId: string;
  receivable: Receivable;
  onChanged: (receivable: Receivable) => void;
}

interface Errors {
  name?: string;
  phone?: string;
}

/** Garants (UC-CRE-07) : nom, téléphone, lien avec le client ; pièce d'identité à venir. */
export function GuarantorsSection({ shopId, receivable, onChanged }: GuarantorsSectionProps) {
  const { gateway } = useReceivablesDeps();
  const titleId = useId();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [relation, setRelation] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [clientId, setClientId] = useState(uuidV7);
  const action = useAction();

  const add = async () => {
    const normalized = normalizePhone(phone);
    const found: Errors = {};
    if (name.trim() === "") found.name = "Le nom est vide";
    if (normalized === null) found.phone = "Le téléphone doit avoir 9 chiffres";
    setErrors(found);
    if (normalized === null || found.name !== undefined) return;
    const body = {
      id: clientId,
      name: name.trim(),
      phone: normalized,
      relation: relation.trim() === "" ? null : relation.trim(),
    };
    const ok = await action.run(async () => {
      onChanged(await gateway.addGuarantor(shopId, receivable.id, body));
    });
    if (ok) {
      setName("");
      setPhone("");
      setRelation("");
      setClientId(uuidV7());
    }
  };

  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Garants
      </h2>
      {receivable.guarantors.length === 0 ? (
        <p className="m-0 text-body text-text-muted">Aucun garant.</p>
      ) : (
        <ul className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card">
          {receivable.guarantors.map((guarantor) => (
            <li key={guarantor.id} className="flex flex-col px-4 py-3">
              <span className="text-lead break-words text-text">{guarantor.name}</span>
              <span className="text-body break-words text-text-muted">
                {guarantor.phone}
                {guarantor.relation === null ? "" : ` · ${guarantor.relation}`}
              </span>
            </li>
          ))}
        </ul>
      )}
      <TextField
        label="Nom du garant"
        autoComplete="off"
        maxLength={120}
        value={name}
        error={errors.name}
        onChange={(event) => {
          setName(event.target.value);
        }}
      />
      <TextField
        label="Téléphone du garant"
        type="tel"
        inputMode="tel"
        autoComplete="off"
        hint={PHONE_HINT}
        value={phone}
        error={errors.phone}
        onChange={(event) => {
          setPhone(event.target.value);
        }}
      />
      <TextField
        label="Lien avec le client (facultatif)"
        hint="Ex. frère, employeur"
        maxLength={200}
        value={relation}
        onChange={(event) => {
          setRelation(event.target.value);
        }}
      />
      <Button variant="ghost" icon={IdCard} disabledReason={ATTACHMENTS_PENDING}>
        Pièce d'identité
      </Button>
      {action.message !== null && <FormMessage text={action.message} />}
      <Button variant="secondary" icon={UserPlus} loading={action.busy} onClick={() => void add()}>
        Ajouter le garant
      </Button>
    </section>
  );
}
