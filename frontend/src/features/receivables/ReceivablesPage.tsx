import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useSearchParams } from "react-router";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import { useSignedIn } from "../../core/services/servicesContext";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { CustomerStatement } from "./CustomerStatement";
import { LegacyReceivable } from "./LegacyReceivable";
import { NewInstallment } from "./NewInstallment";
import { ReceivableDetail } from "./ReceivableDetail";
import { ReceivableList } from "./ReceivableList";
import { VIEW, type ReceivableNav, type ReceivableRole } from "./receivablesNav";
import { loadReferences } from "./references";

/** Section « Créances » (UC-CRE-02 à 09) : liste, fiche, versement, créance ancienne, relevé. */
export function ReceivablesPage({ shopId, role }: { shopId: string; role: ReceivableRole }) {
  const me = useSignedIn();
  const { gateway } = useReceivablesDeps();
  const [params, setParams] = useSearchParams();
  const [round, setRound] = useState(0);
  const refs = useLoad(`${shopId}:${String(round)}`, () =>
    loadReferences(gateway, shopId, { userId: me.userId, name: me.name, role }),
  );

  const nav: ReceivableNav = {
    list: () => {
      setParams({});
    },
    open: (id) => {
      setParams({ vue: VIEW.detail, id });
    },
    pay: (id) => {
      setParams(id === undefined ? { vue: VIEW.pay } : { vue: VIEW.pay, id });
    },
    legacy: () => {
      setParams({ vue: VIEW.legacy });
    },
    statement: (customerId) => {
      setParams({ vue: VIEW.statement, client: customerId });
    },
  };

  if (refs.status !== "ready") {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">Créances</h1>
        {refs.status === "loading" ? (
          <Skeleton lines={4} label="Chargement des créances…" />
        ) : (
          <EmptyState
            message="Connexion nécessaire pour ouvrir les créances."
            action={
              <Button
                variant="secondary"
                icon={RefreshCw}
                onClick={() => {
                  setRound((n) => n + 1);
                }}
              >
                Réessayer
              </Button>
            }
          />
        )}
      </>
    );
  }

  const view = params.get("vue");
  const id = params.get("id");
  const customer = params.get("client");
  const common = { shopId, refs: refs.value, nav };
  if (view === VIEW.detail && id !== null) {
    return <ReceivableDetail key={id} {...common} id={id} />;
  }
  if (view === VIEW.pay) return <NewInstallment key={id ?? "client"} {...common} id={id} />;
  if (view === VIEW.legacy && role === "owner") return <LegacyReceivable {...common} />;
  if (view === VIEW.statement && customer !== null) {
    return <CustomerStatement key={customer} {...common} customerId={customer} />;
  }
  return <ReceivableList {...common} />;
}
