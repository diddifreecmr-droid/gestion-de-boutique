import { useState } from "react";
import { ClipboardList, RotateCcw } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useStockGateway } from "../../core/gateways/httpStock";
import { Button, ChoiceChips } from "../../shared/ui";
import { BackButton, ErrorText, LoadPending, ScreenTitle } from "./Notice";
import { failureText } from "./stockErrors";
import { useStockNav } from "./stockNav";
import { useLoad } from "./useLoad";
import { useStockSubmit } from "./useStockSubmit";

/**
 * Lancer un inventaire (UC-STK-07, étape 1) : choix du lieu, puis comptage. Un seul inventaire
 * en cours par lieu : s'il en existe un, le serveur le désigne et on propose de le reprendre
 * (« il peut s'arrêter et reprendre plus tard »).
 */
export function InventoryStartPage({ shopId }: { shopId: string }) {
  const gateway = useStockGateway();
  const nav = useStockNav();
  const { load, retry } = useLoad(`${shopId}|inventory-start`, () =>
    gateway.matrix(shopId, { text: "", locationId: null, sort: "name" }),
  );
  const [id] = useState(() => uuidV7());
  const [chosen, setChosen] = useState<string | null>(null);
  const submit = useStockSubmit();
  const back = <BackButton label="Retour au stock" onClick={nav.matrix} />;
  if (load.status !== "ready") {
    return (
      <>
        {back}
        <ScreenTitle>Inventaire</ScreenTitle>
        <LoadPending load={load} label="Chargement des lieux…" onRetry={retry} />
      </>
    );
  }
  const locations = load.value.locations;
  const locationId = chosen ?? locations[0]?.location_id ?? null;
  const failure = submit.failure;

  const start = () => {
    if (locationId === null) return;
    void submit.run(
      () => gateway.startInventory(shopId, id, locationId),
      (inventory) => {
        nav.inventory(inventory.id, true);
      },
    );
  };

  return (
    <>
      {back}
      <ScreenTitle>Inventaire</ScreenTitle>
      <p className="m-0 text-body text-text">
        Choisissez le lieu à compter. Les quantités prévues restent cachées pendant le comptage ;
        vous pouvez vous arrêter et reprendre plus tard.
      </p>
      {locations.length === 0 ? (
        <ErrorText text="Aucun lieu actif dans cette boutique : créez d'abord un lieu." />
      ) : (
        <ChoiceChips
          label="Lieu"
          options={locations.map((place) => ({ value: place.location_id, label: place.name }))}
          value={locationId}
          onChange={(value) => {
            setChosen(value);
            submit.clear();
          }}
        />
      )}
      {failure !== null && <ErrorText text={failureText(failure)} />}
      {failure?.kind === "inventoryOpen" && failure.inventoryId !== null && (
        <Button
          variant="secondary"
          fullWidth
          icon={RotateCcw}
          onClick={() => {
            if (failure.inventoryId !== null) nav.inventory(failure.inventoryId);
          }}
        >
          Reprendre l'inventaire en cours
        </Button>
      )}
      <Button
        size="lg"
        fullWidth
        icon={ClipboardList}
        loading={submit.pending}
        onClick={start}
        {...(locationId === null ? { disabledReason: "Aucun lieu à compter" } : {})}
      >
        Lancer l'inventaire
      </Button>
    </>
  );
}
