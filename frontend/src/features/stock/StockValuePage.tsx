import { useState } from "react";
import { PackageX } from "lucide-react";
import { useStockGateway } from "../../core/gateways/httpStock";
import { Button, ChoiceChips } from "../../shared/ui";
import { BackButton, LoadPending, ScreenTitle } from "./Notice";
import { useStockNav } from "./stockNav";
import { useLoad } from "./useLoad";
import { METHODS, worth, type Method } from "./valuation";
import { WorthCard, WorthFacts } from "./WorthCard";

/**
 * Valeur du stock (UC-STK-10, propriétaire et comptable) : vendable par lieu et au total, au
 * CMP avec la vue complémentaire au dernier coût ; abîmé et en route comptés à part.
 */
export function StockValuePage({ shopId }: { shopId: string }) {
  const gateway = useStockGateway();
  const nav = useStockNav();
  const [method, setMethod] = useState<Method>("wac");
  const { load, retry } = useLoad(`${shopId}|value`, () => gateway.value(shopId));
  const back = <BackButton label="Retour au stock" onClick={nav.matrix} />;
  if (load.status !== "ready") {
    return (
      <>
        {back}
        <ScreenTitle>Valeur du stock</ScreenTitle>
        <LoadPending load={load} label="Calcul de la valeur du stock…" onRetry={retry} />
      </>
    );
  }
  const report = load.value;
  const label = method === "wac" ? "au CMP" : "au dernier coût";
  return (
    <>
      {back}
      <ScreenTitle>Valeur du stock</ScreenTitle>
      <ChoiceChips label="Calcul" options={METHODS} value={method} onChange={setMethod} />
      <WorthCard
        label={`Stock vendable, tous lieux, ${label}`}
        worth={worth(report.sellable, method)}
      />
      <h2 className="m-0 text-title-sm font-semibold text-text">Par lieu</h2>
      <ul aria-label="Valeur par lieu" className="m-0 flex list-none flex-col gap-4 p-0">
        {report.locations.map((place) => (
          <li
            key={place.location_id}
            className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card"
          >
            <h3 className="m-0 break-words text-lead font-semibold text-text">
              {place.active ? place.location_name : `${place.location_name} (fermé)`}
            </h3>
            <WorthFacts
              rows={[
                { label: "Vendable", worth: worth(place.sellable, method) },
                { label: "Abîmé", worth: worth(place.damaged, method) },
                { label: "En route", worth: worth(place.incoming, method) },
              ]}
            />
          </li>
        ))}
      </ul>
      <h2 className="m-0 text-title-sm font-semibold text-text">À part</h2>
      <div className="rounded-lg bg-surface p-4 shadow-card">
        <WorthFacts
          rows={[
            { label: "Stock abîmé", worth: worth(report.damaged, method) },
            { label: "Marchandise en route", worth: worth(report.incoming, method) },
          ]}
        />
      </div>
      <Button variant="secondary" fullWidth icon={PackageX} onClick={nav.damaged}>
        Voir le stock abîmé
      </Button>
    </>
  );
}
