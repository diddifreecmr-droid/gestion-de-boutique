/** Erreur levée quand une valeur ne peut pas être affichée sans trahir la donnée (fail-fast). */
export class FormatError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FormatError";
  }
}
