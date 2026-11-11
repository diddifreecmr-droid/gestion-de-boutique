/** Texte comparé sans accents ni casse (« Ngaoundéré » trouvé par « ngaoundere »). */
export function folded(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("fr");
}
