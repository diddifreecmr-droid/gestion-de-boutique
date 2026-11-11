import { useId, useState } from "react";
import { Search, UserPlus, UserRound } from "lucide-react";
import { useGateways } from "../../core/gateways/gateways";
import type { CustomerKind } from "../../core/gateways/salesContract";
import {
  Button,
  ChoiceChips,
  ListCard,
  ListCardRow,
  SearchField,
  TextField,
} from "../../shared/ui";
import type { CustomerDraft } from "./draft";
import { FieldMessage } from "./FieldMessage";
import { PHONE_HINT } from "./phone";
import { useLookup } from "./useLookup";

export interface CustomerErrors {
  customer?: string | undefined;
  name?: string | undefined;
  phone?: string | undefined;
}

export interface CustomerPickerProps {
  shopId: string;
  value: CustomerDraft;
  onChange: (customer: CustomerDraft) => void;
  /** Titre du groupe : « Client » (crédit, obligatoire) ou « Client (facultatif) ». */
  title: string;
  errors: CustomerErrors;
}

const KINDS = [
  { value: "individual", label: "Particulier" },
  { value: "company", label: "Entreprise" },
] as const;

/** Client de la vente : recherche (nom ou téléphone) ou création rapide (UC-VEN-02, H20). */
export function CustomerPicker({ shopId, value, onChange, title, errors }: CustomerPickerProps) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-4">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        {title}
      </h2>
      {value.mode === "existing" && (
        <div className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
          <p className="m-0 flex items-center gap-2 text-lead text-text">
            <UserRound aria-hidden="true" className="size-6 shrink-0" />
            <span>{value.customer.name}</span>
          </p>
          <p className="m-0 text-body text-text-muted">{value.customer.phone}</p>
          <Button
            variant="ghost"
            icon={Search}
            onClick={() => {
              onChange({ mode: "none" });
            }}
          >
            Changer de client
          </Button>
        </div>
      )}
      {value.mode === "new" && <NewCustomer value={value} onChange={onChange} errors={errors} />}
      {value.mode === "none" && <CustomerSearch shopId={shopId} onChange={onChange} />}
      {errors.customer !== undefined && <FieldMessage text={errors.customer} />}
    </section>
  );
}

function CustomerSearch({
  shopId,
  onChange,
}: {
  shopId: string;
  onChange: (customer: CustomerDraft) => void;
}) {
  const { sales } = useGateways();
  const [query, setQuery] = useState("");
  const lookup = useLookup(query, () => sales.searchCustomers(shopId, query));
  const typedPhone = /\d/.test(query);
  return (
    <>
      <SearchField
        label="Chercher un client"
        hint="Nom ou téléphone"
        value={query}
        onChange={setQuery}
      />
      {lookup.status === "offline" && (
        <p className="m-0 text-body text-text-muted">
          Connexion nécessaire pour chercher un client.
        </p>
      )}
      {lookup.status === "ready" && lookup.value.items.length > 0 && (
        <ListCard label="Clients trouvés">
          {lookup.value.items.map((customer) => (
            <ListCardRow
              key={customer.id}
              title={customer.name}
              subtitle={customer.phone}
              onOpen={() => {
                onChange({ mode: "existing", customer });
              }}
            />
          ))}
        </ListCard>
      )}
      <Button
        variant="secondary"
        icon={UserPlus}
        fullWidth
        onClick={() => {
          onChange({
            mode: "new",
            name: typedPhone ? "" : query.trim(),
            phone: typedPhone ? query.trim() : "",
            kind: "individual",
          });
        }}
      >
        Nouveau client
      </Button>
    </>
  );
}

function NewCustomer({
  value,
  onChange,
  errors,
}: {
  value: Extract<CustomerDraft, { mode: "new" }>;
  onChange: (customer: CustomerDraft) => void;
  errors: CustomerErrors;
}) {
  return (
    <>
      <TextField
        label="Nom du client"
        autoComplete="off"
        value={value.name}
        error={errors.name}
        onChange={(event) => {
          onChange({ ...value, name: event.target.value });
        }}
      />
      <TextField
        label="Téléphone du client"
        type="tel"
        inputMode="tel"
        autoComplete="off"
        hint={PHONE_HINT}
        value={value.phone}
        error={errors.phone}
        onChange={(event) => {
          onChange({ ...value, phone: event.target.value });
        }}
      />
      <ChoiceChips<CustomerKind>
        label="Type de client"
        options={KINDS}
        value={value.kind}
        onChange={(kind) => {
          onChange({ ...value, kind });
        }}
      />
      <Button
        variant="ghost"
        icon={Search}
        fullWidth
        onClick={() => {
          onChange({ mode: "none" });
        }}
      >
        Chercher un client existant
      </Button>
    </>
  );
}
