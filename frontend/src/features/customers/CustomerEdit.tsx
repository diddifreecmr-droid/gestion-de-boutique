import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useCustomersGateway } from "../../core/gateways/httpCustomers";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { createBody, EMPTY_CUSTOMER, fieldsOf, patchBody } from "./customerFields";
import { CustomerForm } from "./CustomerForm";
import type { CustomerNav } from "./customersNav";

export function CustomerNew({ shopId, nav }: { shopId: string; nav: CustomerNav }) {
  const gateway = useCustomersGateway();
  const [id] = useState(() => uuidV7()); // même identifiant si l'on renvoie : pas de doublon
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux clients
      </Button>
      <CustomerForm
        title="Nouveau client"
        initial={EMPTY_CUSTOMER}
        submitLabel="Enregistrer le client"
        onSubmit={(fields) => gateway.create(shopId, createBody(fields, id))}
        onSaved={(customer) => {
          nav.open(customer.id);
        }}
      />
    </>
  );
}

export function CustomerEdit({
  shopId,
  id,
  nav,
}: {
  shopId: string;
  id: string;
  nav: CustomerNav;
}) {
  const gateway = useCustomersGateway();
  const sheet = useLoad(`edit|${id}`, () => gateway.sheet(shopId, id));
  const back = (
    <Button
      variant="ghost"
      icon={ArrowLeft}
      onClick={() => {
        nav.open(id);
      }}
    >
      Retour à la fiche
    </Button>
  );
  if (sheet.status !== "ready") {
    return (
      <>
        {back}
        {sheet.status === "loading" ? (
          <Skeleton lines={4} label="Chargement du client…" />
        ) : (
          <EmptyState message="Connexion nécessaire pour modifier ce client." />
        )}
      </>
    );
  }
  const customer = sheet.value.customer;
  return (
    <>
      {back}
      <CustomerForm
        title={`Modifier ${customer.name}`}
        initial={fieldsOf(customer)}
        submitLabel="Enregistrer les changements"
        onSubmit={(fields) => gateway.update(shopId, id, patchBody(customer, fields))}
        onSaved={() => {
          nav.open(id);
        }}
      />
    </>
  );
}
