import { useState } from "react";
import { CirclePlus, Users } from "lucide-react";
import { useCustomersGateway } from "../../core/gateways/httpCustomers";
import { Button, EmptyState, ListCard, ListCardRow, SearchField, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { customerLine } from "./customerFields";
import type { CustomerNav } from "./customersNav";

/** Liste des clients (UC-VEN-11) : recherche par nom ou téléphone, par le serveur. */
export function CustomerList({ shopId, nav }: { shopId: string; nav: CustomerNav }) {
  const gateway = useCustomersGateway();
  const [text, setText] = useState("");
  const query = text.trim();
  const found = useLoad(`${shopId}|${query}`, () => gateway.search(shopId, query));
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Clients</h1>
      <Button size="lg" fullWidth icon={CirclePlus} onClick={nav.create}>
        Nouveau client
      </Button>
      <SearchField
        label="Rechercher un client"
        hint="Nom ou numéro de téléphone"
        value={text}
        onChange={setText}
      />
      {found.status === "loading" && <Skeleton lines={3} label="Recherche des clients…" />}
      {found.status === "offline" && (
        <EmptyState message="Connexion nécessaire pour rechercher les clients." />
      )}
      {found.status === "ready" && found.value.length === 0 && (
        <EmptyState
          icon={Users}
          message={query === "" ? "Aucun client pour l'instant." : "Aucun client ne correspond."}
        />
      )}
      {found.status === "ready" && found.value.length > 0 && (
        <ListCard label="Liste des clients">
          {found.value.map((customer) => (
            <ListCardRow
              key={customer.id}
              title={customer.name}
              subtitle={customerLine(customer)}
              onOpen={() => {
                nav.open(customer.id);
              }}
            />
          ))}
        </ListCard>
      )}
    </>
  );
}
