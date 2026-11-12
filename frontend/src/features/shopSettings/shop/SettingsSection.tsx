import { useId, useState, type ReactNode } from "react";
import { Check } from "lucide-react";
import type { SettingsPatch, ShopSettings } from "../../../core/gateways/shopAdminContract";
import { useShopAdmin } from "../../../core/gateways/httpShopAdmin";
import { Button, useToast } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { useAction } from "../useAction";
import { changesOf } from "./settingsInputs";

export interface SectionProps {
  shopId: string;
  settings: ShopSettings;
  onSaved: (settings: ShopSettings) => void;
}

export interface SettingsSectionProps extends SectionProps {
  title: string;
  /** Champs voulus, ou `null` si une saisie est invalide (erreurs déjà affichées). */
  collect: () => Omit<SettingsPatch, "version"> | null;
  children: ReactNode;
}

/**
 * Un groupe de réglages avec son bouton « Enregistrer » : n'envoie que les champs changés,
 * avec la `version` lue (409 si quelqu'un a réglé la boutique entre-temps).
 */
export function SettingsSection({
  shopId,
  settings,
  onSaved,
  title,
  collect,
  children,
}: SettingsSectionProps) {
  const gateway = useShopAdmin();
  const toast = useToast();
  const titleId = useId();
  const action = useAction();
  const [unchanged, setUnchanged] = useState(false);

  const save = async () => {
    const wanted = collect();
    if (wanted === null) return;
    const patch = changesOf(settings, wanted);
    setUnchanged(Object.keys(patch).length === 0);
    if (Object.keys(patch).length === 0) return;
    await action.run("save", async () => {
      onSaved(await gateway.updateSettings(shopId, { ...patch, version: settings.version }));
      toast.show({ tone: "success", message: `${title} : enregistré.` });
    });
  };

  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        {title}
      </h2>
      {children}
      {unchanged && (
        <p className="m-0 text-body text-text-muted">Aucun changement à enregistrer.</p>
      )}
      {action.message !== null && <FormMessage text={action.message} />}
      <Button
        variant="secondary"
        icon={Check}
        fullWidth
        loading={action.busy === "save"}
        onClick={() => void save()}
      >
        Enregistrer : {title.toLowerCase()}
      </Button>
    </section>
  );
}
