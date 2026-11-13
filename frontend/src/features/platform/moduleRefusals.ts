/**
 * Refus `422` d'un enregistrement de modules (specs § 4.5) : `MODULE_MANDATORY`
 * (`details.module`) et `MODULE_DEPENDENCY` (`details.module`, `details.requires`), dits en
 * français avec le nom des modules tel qu'il est écrit dans la console.
 */
import type { ApiError } from "../../core/api/errors";
import { ALL_MODULES } from "../../core/profile/modules";
import { MODULE_LABELS } from "./moduleTexts";

export const MODULE_MANDATORY = "MODULE_MANDATORY";
export const MODULE_DEPENDENCY = "MODULE_DEPENDENCY";

/** Nom affiché d'un module reçu dans `details`, ou `undefined` si le code est absent/inconnu. */
function labelOf(code: unknown): string | undefined {
  const module = ALL_MODULES.find((known) => known === code);
  return module === undefined ? undefined : `« ${MODULE_LABELS[module]} »`;
}

/** Message d'un refus de modules, ou `undefined` si l'erreur n'en est pas un. */
export function moduleRefusal(error: ApiError): string | undefined {
  if (error.code === MODULE_MANDATORY) {
    const module = labelOf(error.details["module"]);
    return module === undefined
      ? "Un module toujours actif manque : la boutique ne peut pas s'en passer. Rien n'a été enregistré."
      : `Le module ${module} est toujours actif : il ne peut pas être retiré. Rien n'a été enregistré.`;
  }
  if (error.code === MODULE_DEPENDENCY) {
    const module = labelOf(error.details["module"]);
    const requires = labelOf(error.details["requires"]);
    if (module === undefined || requires === undefined) {
      return "Un module a besoin d'un autre module qui n'est pas activé. Rien n'a été enregistré.";
    }
    return `Le module ${module} a besoin du module ${requires} : activez-le aussi, ou désactivez ${module}. Rien n'a été enregistré.`;
  }
  return undefined;
}
