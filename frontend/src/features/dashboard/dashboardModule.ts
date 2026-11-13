/**
 * Module `dashboard` de la boutique (specs § 15.1, « Modules par boutique ») : seul
 * l'administrateur plateforme l'active. Sans lui, aucun point d'entrée vers le tableau de bord
 * complet n'apparaît. Lu dans la source unique `useModules()` (fournie par la coquille, qui lit
 * `enabled_modules` et le garde pour le hors connexion) : aucun appel réseau ici.
 */
import { useModules } from "../../core/profile/modulesContext";
import type { Figures } from "./reportingContext";

export const DASHBOARD_MODULE = "dashboard";

/** Le module `dashboard` est-il actif ? Toujours « prêt » : la coquille a déjà lu les modules. */
export function useDashboardModule(): Figures<boolean> {
  const modules = useModules();
  return {
    loaded: { status: "ready", value: modules.has(DASHBOARD_MODULE) },
    retry: () => {
      throw new Error("useDashboardModule : rien à relire, les modules viennent de la coquille");
    },
  };
}
