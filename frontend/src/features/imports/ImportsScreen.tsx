import { useState } from "react";
import { FileSpreadsheet } from "lucide-react";
import type { Role } from "../../core/auth/me";
import { Button } from "../../shared/ui";
import { ImportHistory } from "./ImportHistory";
import type { ImportModel } from "./importModels";
import { ImportsPage } from "./ImportsPage";
import type { SaveFile } from "./saveFile";

export const NEW_IMPORT_LABEL = "Nouvel import";

export interface ImportsScreenProps {
  shopId: string;
  role: Role;
  models: readonly ImportModel[];
  save: SaveFile;
  /** Jour métier à Douala (« AAAA-MM-JJ »). */
  today: string;
}

/**
 * Écran d'import : nouvel import en 4 étapes (T44) ou « Imports passés » (T45). Seul le
 * propriétaire peut annuler un lot (UC-IMP-03).
 */
export function ImportsScreen({ shopId, role, models, save, today }: ImportsScreenProps) {
  const [view, setView] = useState<"new" | "history">("new");
  if (view === "new") {
    return (
      <ImportsPage
        shopId={shopId}
        models={models}
        save={save}
        onHistory={() => {
          setView("history");
        }}
      />
    );
  }
  return (
    <>
      <Button
        variant="ghost"
        icon={FileSpreadsheet}
        onClick={() => {
          setView("new");
        }}
      >
        {NEW_IMPORT_LABEL}
      </Button>
      <ImportHistory shopId={shopId} today={today} canCancel={role === "owner"} save={save} />
    </>
  );
}
