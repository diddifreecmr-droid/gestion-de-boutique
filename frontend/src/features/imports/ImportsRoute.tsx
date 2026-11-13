import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { createHttpImports, ImportsContext } from "../../core/gateways/httpImports";
import { useModules } from "../../core/profile/modulesContext";
import { useServices } from "../../core/services/servicesContext";
import { modelsFor } from "./importModels";
import { ImportsPage } from "./ImportsPage";
import { saveInBrowser } from "./saveFile";

/**
 * Entrée de route « Import » (chargée à la demande, specs § 4.6). La section ne l'ouvre que si
 * le module `import` est actif et que le rôle a des modèles (`ImportsSection`).
 */
export default function ImportsRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const modules = useModules();
  const gateway = useMemo(() => createHttpImports(services), [services]);
  const models = useMemo(() => modelsFor(role, modules), [role, modules]);
  return (
    <ImportsContext.Provider value={gateway}>
      <ImportsPage shopId={shopId} models={models} save={saveInBrowser} />
    </ImportsContext.Provider>
  );
}
