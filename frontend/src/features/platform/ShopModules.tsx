import { useId, useState } from "react";
import { Save } from "lucide-react";
import {
  ALWAYS_ON,
  OPTIONAL_MODULES,
  shopModules,
  type ModuleCode,
} from "../../core/profile/modules";
import { Badge, Button, ListCard, ListCardRow, Switch } from "../../shared/ui";
import { changeSummary, dependencyHint, MODULE_LABELS, modulesBody, toggle } from "./moduleTexts";

export interface ShopModulesProps {
  /** `enabled_modules` lus du serveur (la fiche est remontée après chaque enregistrement). */
  enabled: readonly string[];
  busy: boolean;
  onSave: (modules: ModuleCode[]) => void;
}

/**
 * Modules de la boutique (décision client du 12/11/2026) : socle, journal, catalogue et ventes
 * toujours actifs ; les autres par interrupteur, dépendances comprises. Avant d'enregistrer,
 * une phrase par module dit ce qui disparaît (ou réapparaît) ; les données sont gardées.
 */
export function ShopModules({ enabled, busy, onSave }: ShopModulesProps) {
  const [initial] = useState(() => shopModules(enabled).enabled);
  const [draft, setDraft] = useState<ReadonlySet<ModuleCode>>(initial);
  const titleId = useId();
  const summary = changeSummary(initial, draft);
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-4">
      <h2 id={titleId} className="m-0 text-title-sm font-bold text-text">
        Modules
      </h2>
      <ListCard label="Modules toujours actifs">
        {ALWAYS_ON.map((module) => (
          <ListCardRow
            key={module}
            title={MODULE_LABELS[module]}
            subtitle="Ne se désactive pas"
            badge={<Badge status="success">Toujours actif</Badge>}
          />
        ))}
      </ListCard>
      <div role="group" aria-label="Modules facultatifs" className="flex flex-col gap-2">
        {OPTIONAL_MODULES.map((module) => (
          <Switch
            key={module}
            label={MODULE_LABELS[module]}
            checked={draft.has(module)}
            {...withHint(dependencyHint(module))}
            onChange={(on) => {
              setDraft(toggle(draft, module, on));
            }}
          />
        ))}
      </div>
      {summary.length > 0 && (
        <div aria-live="polite" className="flex flex-col gap-2 rounded-lg bg-warning-soft p-4">
          <p className="m-0 text-label font-semibold text-warning-text">En enregistrant :</p>
          <ul className="m-0 flex list-disc flex-col gap-1 pl-6">
            {summary.map((line) => (
              <li key={line} className="text-body text-text">
                {line}
              </li>
            ))}
          </ul>
        </div>
      )}
      <Button
        variant="primary"
        icon={Save}
        fullWidth
        loading={busy}
        {...(summary.length === 0 ? { disabledReason: "Aucun changement à enregistrer." } : {})}
        onClick={() => {
          onSave(modulesBody(draft));
        }}
      >
        Enregistrer les modules
      </Button>
    </section>
  );
}

function withHint(hint: string | undefined): { hint?: string } {
  return hint === undefined ? {} : { hint };
}
