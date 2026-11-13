/**
 * Blocs des chiffres liés à un module facultatif (specs § 4.5, § 15.1) : dans `GET /dashboard`
 * et `GET /home`, le bloc d'un module éteint vaut `null`. Un bloc `null` ne s'affiche pas — ni
 * carte, ni ligne, ni « 0 » — et n'est jamais remplacé par zéro.
 *
 * Cohérence avec la source unique `useModules()` : un bloc ne se montre que s'il est reçu **et**
 * que son module est actif pour la coquille. Si les deux sources divergent (modules gardés hors
 * connexion, réglage changé entre deux lectures), le bloc reste caché : aucun point d'entrée
 * d'un module éteint n'apparaît.
 */
import type { ModuleCode } from "../../core/profile/modules";
import { useModules } from "../../core/profile/modulesContext";

/** `shown(bloc, module)` : le bloc à afficher, ou `null` s'il ne doit pas apparaître. */
export type ShownBlock = <T>(block: T | null, module: ModuleCode) => T | null;

export function useShownBlock(): ShownBlock {
  const modules = useModules();
  return <T>(block: T | null, module: ModuleCode): T | null =>
    block !== null && modules.has(module) ? block : null;
}
