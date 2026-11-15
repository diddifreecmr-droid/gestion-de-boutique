import { useState, type FormEvent } from "react";
import { CirclePlus } from "lucide-react";
import type { ArticleForm, FabricResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { useActivePieceWords } from "../../core/profile/activeProfile";
import { Button, TextField } from "../../shared/ui";
import { catalogRights, type CatalogRole } from "./catalogRights";
import { ColorsInput } from "./ColorsInput";
import { NO_PRICES } from "./createPrices";
import { createBody, createErrors, type FabricSettings } from "./fabricDraft";
import { FabricSettingsFields } from "./FabricSettingsFields";
import { SubmitFailureNotice } from "./SubmitFailureNotice";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface FabricCreateFormProps {
  shopId: string;
  role: CatalogRole;
  form: ArticleForm;
  onCreated: (fabric: FabricResponse) => void;
  onOpenExisting: (articleId: string) => void;
}

const EMPTY: FabricSettings = {
  rollLength: "",
  meterOnly: false,
  threshold: "",
  prices: NO_PRICES,
};

/**
 * « Nouveau tissu » (Textile, 2026-11-15) : le nom du tissu et ses couleurs en saisie rapide,
 * puis les réglages communs. Le serveur crée un article par couleur (« Djampar — Rouge »).
 */
export function FabricCreateForm(props: FabricCreateFormProps) {
  const { shopId, role, form } = props;
  const gateway = useCatalogAdmin();
  const submit = useCatalogSubmit();
  const words = useActivePieceWords();
  const [fabric, setFabric] = useState("");
  const [colors, setColors] = useState<string[]>([]);
  const [settings, setSettings] = useState(EMPTY);
  const [checked, setChecked] = useState(false);
  const errors = checked ? createErrors(fabric, colors, settings) : {};
  const rights = {
    setPrices: catalogRights(role).setPrices,
    minPriceEnabled: form.minPriceEnabled,
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setChecked(true);
    if (Object.keys(createErrors(fabric, colors, settings)).length > 0) return;
    const body = createBody(fabric, colors, settings, rights);
    void submit.run(() => gateway.createFabric(shopId, body), props.onCreated);
  }

  return (
    <form noValidate aria-label="Nouveau tissu" className="flex flex-col gap-4" onSubmit={onSubmit}>
      <TextField
        label="Nom du tissu"
        hint="Par exemple Djampar, Getzner, Wax"
        autoComplete="off"
        value={fabric}
        error={errors.fabric}
        onChange={(event) => {
          setFabric(event.target.value);
        }}
      />
      <ColorsInput value={colors} onChange={setColors} error={errors.colors} />
      {colors.length > 0 && fabric.trim() !== "" && (
        <p className="m-0 text-body text-text-muted">
          {colors.length > 1
            ? `${String(colors.length)} articles seront créés`
            : "1 article sera créé"}{" "}
          : {colors.map((color) => `${fabric.trim()} — ${color}`).join(", ")}
        </p>
      )}
      <FabricSettingsFields
        value={settings}
        onChange={setSettings}
        errors={errors}
        words={words}
        setPrices={rights.setPrices}
        minPriceEnabled={rights.minPriceEnabled}
      />
      {submit.failure !== null && (
        <SubmitFailureNotice
          failure={submit.failure}
          onOpenExisting={props.onOpenExisting}
          onReload={() => {
            throw new Error("Une création ne peut pas produire de conflit de version");
          }}
        />
      )}
      <Button type="submit" size="lg" fullWidth icon={CirclePlus} loading={submit.pending}>
        Créer le tissu
      </Button>
    </form>
  );
}
