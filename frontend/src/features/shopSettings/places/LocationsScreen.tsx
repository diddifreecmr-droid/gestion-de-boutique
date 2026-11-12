import { useState } from "react";
import { Plus } from "lucide-react";
import { uuidV7 } from "../../../core/api/uuidv7";
import type { LocationPatch, ShopLocation } from "../../../core/gateways/shopAdminContract";
import { useShopAdmin } from "../../../core/gateways/httpShopAdmin";
import { Button } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { useLoad } from "../../expenses/useLoad";
import { ScreenFrame } from "../ScreenFrame";
import type { SettingsScreenProps } from "../settingsNav";
import { useAction } from "../useAction";
import { LocationFields } from "./LocationFields";
import { EMPTY_LOCATION, type LocationDraft } from "./locationDraft";
import { LocationRow } from "./LocationRow";
import { mergeById } from "./mergeById";

/**
 * Lieux (UC-SOC-05) : boutiques et entrepôts, point de vente ou non. Le serveur refuse de
 * désactiver le dernier point de vente ou un lieu qui garde du stock : le message le dit.
 */
export function LocationsScreen({ shopId, onBack }: SettingsScreenProps) {
  const gateway = useShopAdmin();
  const [round, setRound] = useState(0);
  const loaded = useLoad(`${shopId}:${String(round)}`, () => gateway.locations(shopId));
  const [changed, setChanged] = useState<ShopLocation[]>([]);
  const [draft, setDraft] = useState<LocationDraft>(EMPTY_LOCATION);
  const [nameError, setNameError] = useState<string | undefined>(undefined);
  const action = useAction();

  return (
    <ScreenFrame
      title="Lieux"
      onBack={onBack}
      loaded={loaded}
      onRetry={() => {
        setRound((n) => n + 1);
      }}
    >
      {(initial) => {
        const locations = mergeById(initial, changed);
        const keep = (location: ShopLocation) => {
          setChanged((current) => [...current.filter((l) => l.id !== location.id), location]);
        };
        const patch = (location: ShopLocation, change: Omit<LocationPatch, "version">) =>
          action.run(location.id, async () => {
            keep(
              await gateway.updateLocation(shopId, location.id, {
                ...change,
                version: location.version,
              }),
            );
          });
        const add = async () => {
          if (draft.name.trim() === "") {
            setNameError("Le nom est vide");
            return;
          }
          const city = draft.city.trim();
          const order = Math.max(0, ...locations.map((l) => l.display_order)) + 1;
          const done = await action.run("new", async () => {
            keep(
              await gateway.createLocation(shopId, {
                id: uuidV7(),
                name: draft.name.trim(),
                kind: draft.kind,
                is_point_of_sale: draft.isPointOfSale,
                city: city === "" ? null : city,
                display_order: order,
              }),
            );
          });
          if (done) setDraft(EMPTY_LOCATION);
        };
        return (
          <>
            <ul
              aria-label="Lieux de la boutique"
              className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card"
            >
              {locations.map((location) => (
                <LocationRow
                  key={location.id}
                  location={location}
                  busy={action.busy === location.id}
                  onPatch={(change) => patch(location, change)}
                />
              ))}
            </ul>
            {action.message !== null && <FormMessage text={action.message} />}
            <section aria-labelledby="new-location" className="flex flex-col gap-4">
              <h2 id="new-location" className="m-0 text-title-sm font-semibold text-text">
                Nouveau lieu
              </h2>
              <LocationFields
                prefix="Nouveau lieu"
                draft={draft}
                nameError={nameError}
                onChange={(next) => {
                  setDraft(next);
                  setNameError(undefined);
                }}
              />
              <Button
                variant="secondary"
                icon={Plus}
                fullWidth
                loading={action.busy === "new"}
                onClick={() => void add()}
              >
                Ajouter le lieu
              </Button>
            </section>
          </>
        );
      }}
    </ScreenFrame>
  );
}
