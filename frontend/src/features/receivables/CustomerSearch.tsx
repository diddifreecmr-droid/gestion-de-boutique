import { useState } from "react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { CustomerSummary } from "../../core/gateways/receivablesContract";
import { ListCard, ListCardRow, SearchField } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";

/** Recherche d'un client existant par nom ou téléphone (UC-CRE-03 étape 1). */
export function CustomerSearch({
  shopId,
  onPick,
}: {
  shopId: string;
  onPick: (customer: CustomerSummary) => void;
}) {
  const { gateway } = useReceivablesDeps();
  const [query, setQuery] = useState("");
  const found = useLoad(query, () => gateway.searchCustomers(shopId, query));
  return (
    <>
      <SearchField
        label="Chercher le client"
        hint="Nom ou téléphone"
        value={query}
        onChange={setQuery}
      />
      {found.status === "offline" && (
        <p className="m-0 text-body text-text-muted">
          Connexion nécessaire pour chercher un client.
        </p>
      )}
      {found.status === "ready" && query.trim() !== "" && found.value.length === 0 && (
        <p className="m-0 text-body text-text-muted">Aucun client trouvé.</p>
      )}
      {found.status === "ready" && found.value.length > 0 && (
        <ListCard label="Clients trouvés">
          {found.value.map((customer) => (
            <ListCardRow
              key={customer.id}
              title={customer.name}
              subtitle={customer.phone}
              onOpen={() => {
                onPick(customer);
              }}
            />
          ))}
        </ListCard>
      )}
    </>
  );
}
