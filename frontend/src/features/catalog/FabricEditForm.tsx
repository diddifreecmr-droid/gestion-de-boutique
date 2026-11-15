import { useState, type FormEvent } from "react";
import { Save } from "lucide-react";
import type { ArticleForm, ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { useActivePieceWords } from "../../core/profile/activeProfile";
import { Button, useToast } from "../../shared/ui";
import { VERSION_CONFLICT_MESSAGE } from "./catalogErrors";
import { catalogRights, type CatalogRole } from "./catalogRights";
import { patchBody, settingsErrors, settingsOf } from "./fabricDraft";
import { FabricSettingsFields } from "./FabricSettingsFields";
import { InlineMessage } from "./InlineMessage";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface FabricEditFormProps {
  shopId: string;
  role: CatalogRole;
  fabric: string;
  form: ArticleForm;
  /** Une couleur du tissu : elles partagent prix, longueur et seuil. */
  sample: ArticleResponse;
  /** Toutes les couleurs après l'enregistrement (réponse du serveur). */
  onSaved: (colors: ArticleResponse[]) => void;
}

/** « Modifier le tissu » : prix, longueur du rouleau, seuil — appliqués à toutes les couleurs. */
export function FabricEditForm(props: FabricEditFormProps) {
  const { shopId, fabric, form } = props;
  const gateway = useCatalogAdmin();
  const toast = useToast();
  const submit = useCatalogSubmit();
  const words = useActivePieceWords();
  const [settings, setSettings] = useState(() => settingsOf(props.sample));
  const [checked, setChecked] = useState(false);
  const errors = checked ? settingsErrors(settings) : {};
  const rights = {
    setPrices: catalogRights(props.role).setPrices,
    minPriceEnabled: form.minPriceEnabled,
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setChecked(true);
    if (Object.keys(settingsErrors(settings)).length > 0) return;
    void submit.run(
      () => gateway.updateFabric(shopId, fabric, patchBody(settings, rights)),
      (response) => {
        const count = response.items.length;
        const scope = count > 1 ? `ses ${String(count)} couleurs` : "sa couleur";
        toast.show({ tone: "success", message: `${fabric} enregistré pour ${scope}` });
        props.onSaved(response.items);
      },
    );
  }

  const failure = submit.failure;
  return (
    <form
      noValidate
      aria-label="Modifier le tissu"
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
      onSubmit={onSubmit}
    >
      <h2 className="m-0 text-title-sm font-semibold text-text">Modifier le tissu</h2>
      <p className="m-0 text-body text-text-muted">S'applique à toutes les couleurs de {fabric}.</p>
      <FabricSettingsFields
        value={settings}
        onChange={setSettings}
        errors={errors}
        words={words}
        setPrices={rights.setPrices}
        minPriceEnabled={rights.minPriceEnabled}
      />
      {failure !== null && (
        <InlineMessage
          text={
            failure.kind === "message"
              ? failure.text
              : failure.kind === "conflict"
                ? VERSION_CONFLICT_MESSAGE
                : `Conflit avec ${failure.existingName}`
          }
        />
      )}
      <Button type="submit" size="lg" fullWidth icon={Save} loading={submit.pending}>
        Enregistrer le tissu
      </Button>
    </form>
  );
}
