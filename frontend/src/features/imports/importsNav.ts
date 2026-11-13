/**
 * Adresse de l'écran d'import (`/s/{id}/import`). Module léger : la coquille l'importe sans
 * charger l'écran. Le serveur ne sert **pas encore** de code de menu pour l'import (aucune
 * entrée dans les profils) : l'écran n'est atteignable que par cette adresse, et seulement si
 * le module `import` de la boutique est actif (`useModules().has("import")`, T46).
 */
export const IMPORTS_KEY = "import";
export const IMPORT_MODULE = "import";
