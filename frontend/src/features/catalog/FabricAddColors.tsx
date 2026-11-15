import { useState } from "react";
import { CirclePlus } from "lucide-react";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button, useToast } from "../../shared/ui";
import { VERSION_CONFLICT_MESSAGE, type SubmitFailure } from "./catalogErrors";
import { ColorsInput } from "./ColorsInput";
import { colorOf } from "./fabricGroups";
import { InlineMessage } from "./InlineMessage";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface FabricAddColorsProps {
  shopId: string;
  fabric: string;
  /** Couleurs déjà en boutique (articles du tissu). */
  colors: readonly ArticleResponse[];
  /** Toutes les couleurs du tissu après l'ajout (réponse du serveur). */
  onAdded: (colors: ArticleResponse[]) => void;
}

function failureText(failure: SubmitFailure): string {
  if (failure.kind === "duplicate") return `Cette couleur existe déjà : ${failure.existingName}`;
  if (failure.kind === "conflict") return VERSION_CONFLICT_MESSAGE;
  return failure.text;
}

/** « Ajouter une couleur » : le nouvel article reprend prix, longueur et seuil du tissu. */
export function FabricAddColors({ shopId, fabric, colors, onAdded }: FabricAddColorsProps) {
  const gateway = useCatalogAdmin();
  const toast = useToast();
  const submit = useCatalogSubmit();
  const [added, setAdded] = useState<string[]>([]);
  const [empty, setEmpty] = useState(false);
  const send = () => {
    if (added.length === 0) {
      setEmpty(true);
      return;
    }
    void submit.run(
      () => gateway.addColors(shopId, fabric, added),
      (response) => {
        toast.show({
          tone: "success",
          message: `Couleur ajoutée à ${fabric} : ${added.join(", ")}`,
        });
        setAdded([]);
        onAdded(response.items);
      },
    );
  };
  return (
    <section aria-label="Ajouter une couleur" className="flex flex-col gap-4">
      <h2 className="m-0 text-title-sm font-semibold text-text">Ajouter une couleur</h2>
      <ColorsInput
        value={added}
        existing={colors.map(colorOf)}
        error={empty && added.length === 0 ? "Ajoutez au moins une couleur" : undefined}
        onChange={(next) => {
          setEmpty(false);
          setAdded(next);
        }}
      />
      {submit.failure !== null && <InlineMessage text={failureText(submit.failure)} />}
      <Button
        variant="secondary"
        fullWidth
        icon={CirclePlus}
        loading={submit.pending}
        onClick={send}
      >
        Ajouter à {fabric}
      </Button>
    </section>
  );
}
