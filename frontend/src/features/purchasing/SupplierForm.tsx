import { useState } from "react";
import { Check } from "lucide-react";
import type { Supplier } from "../../core/gateways/purchasingContract";
import { ActionBar, Button, Disclosure, TextField } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import { purchaseErrorMessage } from "./purchaseErrors";

export interface SupplierFields {
  name: string;
  phone: string;
  city: string;
  country: string;
  note: string;
}

export const NAME_EMPTY = "Le nom du fournisseur est vide";

export interface SupplierFormProps {
  title: string;
  initial: SupplierFields;
  submitLabel: string;
  onSubmit: (fields: SupplierFields) => Promise<Supplier>;
  onSaved: (supplier: Supplier) => void;
}

const FIELDS: readonly { key: keyof SupplierFields; label: string; max: number }[] = [
  { key: "phone", label: "Téléphone", max: 120 },
  { key: "city", label: "Ville", max: 120 },
  { key: "country", label: "Pays", max: 120 },
  { key: "note", label: "Note", max: 500 },
];

/** Fiche d'identité d'un fournisseur (UC-ACH-02) : le nom, le reste sous « Plus de détails ». */
export function SupplierForm({
  title,
  initial,
  submitLabel,
  onSubmit,
  onSaved,
}: SupplierFormProps) {
  const [fields, setFields] = useState(initial);
  const [checked, setChecked] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const nameError = fields.name.trim() === "" ? NAME_EMPTY : undefined;
  const filled = FIELDS.some(({ key }) => initial[key] !== "");

  const submit = async () => {
    setChecked(true);
    if (pending || nameError !== undefined) return;
    setPending(true);
    setMessage(null);
    try {
      onSaved(await onSubmit(fields));
    } catch (error) {
      try {
        setMessage(purchaseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setPending(false);
    }
  };

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <TextField
        label="Nom du fournisseur"
        required
        maxLength={120}
        value={fields.name}
        error={checked ? nameError : undefined}
        onChange={(event) => {
          setFields({ ...fields, name: event.target.value });
        }}
      />
      <Disclosure defaultOpen={filled}>
        {FIELDS.map(({ key, label, max }) => (
          <TextField
            key={key}
            label={label}
            maxLength={max}
            {...(key === "phone" ? { type: "tel", inputMode: "tel" as const } : {})}
            value={fields[key]}
            onChange={(event) => {
              setFields({ ...fields, [key]: event.target.value });
            }}
          />
        ))}
      </Disclosure>
      {message !== null && <FormMessage text={message} />}
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button size="lg" fullWidth icon={Check} loading={pending} onClick={() => void submit()}>
            {submitLabel}
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
