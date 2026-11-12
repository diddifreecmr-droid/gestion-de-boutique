import { useState } from "react";
import { Check } from "lucide-react";
import type { Customer } from "../../core/gateways/customersContract";
import { ActionBar, Button, ChoiceChips, Disclosure, TextField } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import type { CustomerFields } from "./customerFields";
import { customerErrorMessage } from "./customersNav";

const KINDS = [
  { value: "individual", label: "Particulier" },
  { value: "company", label: "Entreprise" },
] as const;

const OPTIONAL: readonly { key: "city" | "address" | "note"; label: string; max: number }[] = [
  { key: "city", label: "Ville", max: 200 },
  { key: "address", label: "Adresse", max: 200 },
  { key: "note", label: "Note", max: 500 },
];

export interface CustomerFormProps {
  title: string;
  initial: CustomerFields;
  submitLabel: string;
  onSubmit: (fields: CustomerFields) => Promise<Customer>;
  onSaved: (customer: Customer) => void;
}

/** Saisie d'un client (UC-VEN-11) : nom et téléphone obligatoires, le reste sous « Plus de détails ». */
export function CustomerForm({
  title,
  initial,
  submitLabel,
  onSubmit,
  onSaved,
}: CustomerFormProps) {
  const [fields, setFields] = useState(initial);
  const [checked, setChecked] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const nameError = fields.name.trim() === "" ? "Le nom du client est vide" : undefined;
  const phoneError = fields.phone.trim() === "" ? "Le numéro de téléphone est vide" : undefined;

  const submit = async () => {
    setChecked(true);
    if (pending || nameError !== undefined || phoneError !== undefined) return;
    setPending(true);
    setMessage(null);
    try {
      onSaved(await onSubmit(fields));
    } catch (error) {
      try {
        setMessage(customerErrorMessage(error));
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
        label="Nom du client"
        required
        maxLength={120}
        value={fields.name}
        error={checked ? nameError : undefined}
        onChange={(event) => {
          setFields({ ...fields, name: event.target.value });
        }}
      />
      <TextField
        label="Téléphone"
        required
        type="tel"
        inputMode="tel"
        maxLength={32}
        value={fields.phone}
        error={checked ? phoneError : undefined}
        onChange={(event) => {
          setFields({ ...fields, phone: event.target.value });
        }}
      />
      <ChoiceChips
        label="Type de client"
        options={KINDS}
        value={fields.kind}
        onChange={(kind) => {
          setFields({ ...fields, kind });
        }}
      />
      <Disclosure defaultOpen={OPTIONAL.some(({ key }) => initial[key] !== "")}>
        {OPTIONAL.map(({ key, label, max }) => (
          <TextField
            key={key}
            label={label}
            maxLength={max}
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
