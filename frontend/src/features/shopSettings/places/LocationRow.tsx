import { useState } from "react";
import { Ban, Check, Pencil, RotateCcw } from "lucide-react";
import type { LocationPatch, ShopLocation } from "../../../core/gateways/shopAdminContract";
import { Badge, Button } from "../../../shared/ui";
import { LocationFields } from "./LocationFields";
import { KIND_LABELS, type LocationDraft } from "./locationDraft";

export interface LocationRowProps {
  location: ShopLocation;
  busy: boolean;
  onPatch: (patch: Omit<LocationPatch, "version">) => Promise<boolean>;
}

function draftOf(location: ShopLocation): LocationDraft {
  return {
    name: location.name,
    kind: location.kind === "warehouse" ? "warehouse" : "store",
    isPointOfSale: location.is_point_of_sale,
    city: location.city ?? "",
  };
}

/** Un lieu : modifier (nom, type, point de vente, ville), désactiver ou réactiver. */
export function LocationRow({ location, busy, onPatch }: LocationRowProps) {
  const [draft, setDraft] = useState<LocationDraft | null>(null);
  const [error, setError] = useState<string | undefined>(undefined);
  const kind = location.kind === "warehouse" ? "warehouse" : "store";

  const save = async () => {
    if (draft === null) return;
    if (draft.name.trim() === "") {
      setError("Le nom est vide");
      return;
    }
    const city = draft.city.trim();
    const done = await onPatch({
      name: draft.name.trim(),
      kind: draft.kind,
      is_point_of_sale: draft.isPointOfSale,
      city: city === "" ? null : city,
    });
    if (done) setDraft(null);
  };

  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <span className="flex flex-wrap items-center gap-2">
        <span className={`text-lead ${location.active ? "text-text" : "text-text-muted"}`}>
          {location.name}
        </span>
        {location.is_point_of_sale && <Badge status="success">Point de vente</Badge>}
        {!location.active && <Badge status="danger">Désactivé</Badge>}
      </span>
      <span className="text-body text-text-muted">
        {KIND_LABELS[kind]}
        {location.city !== null && ` · ${location.city}`}
      </span>
      {draft !== null ? (
        <div className="flex flex-col gap-4">
          <LocationFields
            prefix={`Modifier ${location.name}`}
            draft={draft}
            nameError={error}
            onChange={(next) => {
              setDraft(next);
              setError(undefined);
            }}
          />
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              fullWidth
              onClick={() => {
                setDraft(null);
              }}
            >
              Retour
            </Button>
            <Button
              variant="secondary"
              icon={Check}
              fullWidth
              loading={busy}
              onClick={() => void save()}
            >
              Enregistrer
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            icon={Pencil}
            onClick={() => {
              setDraft(draftOf(location));
            }}
          >
            Modifier
          </Button>
          <Button
            variant="secondary"
            icon={location.active ? Ban : RotateCcw}
            loading={busy}
            onClick={() => void onPatch({ active: !location.active })}
          >
            {location.active ? "Désactiver" : "Réactiver"}
          </Button>
        </div>
      )}
    </li>
  );
}
