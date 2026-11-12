import { useMemo } from "react";
import { useSearchParams } from "react-router";
import { createHttpCustomers, CustomersContext } from "../../core/gateways/httpCustomers";
import { useServices } from "../../core/services/servicesContext";
import { CustomerEdit, CustomerNew } from "./CustomerEdit";
import { CustomerList } from "./CustomerList";
import { CustomerSheet } from "./CustomerSheet";
import { customerNav, VIEW } from "./customersNav";

function CustomersPage({ shopId }: { shopId: string }) {
  const [params, setParams] = useSearchParams();
  const nav = customerNav(setParams);
  const view = params.get("vue");
  const id = params.get("id");
  if (view === VIEW.create) return <CustomerNew shopId={shopId} nav={nav} />;
  if (id !== null && view === VIEW.edit)
    return <CustomerEdit key={id} shopId={shopId} id={id} nav={nav} />;
  if (id !== null) return <CustomerSheet key={id} shopId={shopId} id={id} nav={nav} />;
  return <CustomerList shopId={shopId} nav={nav} />;
}

/** Entrée de route « Clients » (« Plus » du propriétaire, chargée à la demande). */
export default function CustomersRoute({ shopId }: { shopId: string }) {
  const services = useServices();
  const gateway = useMemo(() => createHttpCustomers(services), [services]);
  return (
    <CustomersContext.Provider value={gateway}>
      <CustomersPage shopId={shopId} />
    </CustomersContext.Provider>
  );
}
