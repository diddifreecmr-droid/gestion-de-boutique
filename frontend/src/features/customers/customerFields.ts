/** Champs d'un client et corps des requêtes `POST` / `PATCH /customers` (UC-VEN-11). */
import type {
  Customer,
  CustomerChanges,
  CustomerInput,
  CustomerKind,
} from "../../core/gateways/customersContract";

export interface CustomerFields {
  name: string;
  phone: string;
  kind: CustomerKind;
  city: string;
  address: string;
  note: string;
}

export const EMPTY_CUSTOMER: CustomerFields = {
  name: "",
  phone: "",
  kind: "individual",
  city: "",
  address: "",
  note: "",
};

export function fieldsOf(customer: Customer): CustomerFields {
  return {
    name: customer.name,
    phone: customer.phone,
    kind: customer.kind === "company" ? "company" : "individual",
    city: customer.city ?? "",
    address: customer.address ?? "",
    note: customer.note ?? "",
  };
}

/** Téléphone et ville : la sous-ligne d'un client. */
export function customerLine(customer: Customer): string {
  return [customer.phone, customer.city].filter((part) => part !== null && part !== "").join(" · ");
}

const orNull = (value: string) => (value.trim() === "" ? null : value.trim());

/** Corps de `POST /customers` : l'identifiant client (UUID v7) rend la création rejouable. */
export function createBody(fields: CustomerFields, id: string): CustomerInput {
  return {
    id,
    name: fields.name.trim(),
    phone: fields.phone.trim(),
    kind: fields.kind,
    city: orNull(fields.city),
    address: orNull(fields.address),
    note: orNull(fields.note),
  };
}

/** Corps de `PATCH` : **seulement** les champs changés, avec la version lue (verrou optimiste). */
export function patchBody(before: Customer, fields: CustomerFields): CustomerChanges {
  const old = fieldsOf(before);
  const patch: CustomerChanges = { version: before.version };
  if (fields.name.trim() !== old.name) patch.name = fields.name.trim();
  if (fields.phone.trim() !== old.phone) patch.phone = fields.phone.trim();
  if (fields.kind !== old.kind) patch.kind = fields.kind;
  if (fields.city.trim() !== old.city) patch.city = orNull(fields.city);
  if (fields.address.trim() !== old.address) patch.address = orNull(fields.address);
  if (fields.note.trim() !== old.note) patch.note = orNull(fields.note);
  return patch;
}
