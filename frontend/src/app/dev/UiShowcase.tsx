import { ButtonGallery } from "./ButtonGallery";
import { TokenPalette } from "./TokenPalette";

/**
 * Vitrine `/_ui` (développement uniquement, jamais dans le build de production).
 * Référence visuelle pour la QA : chaque composant et chacun de ses états (§ 9.2-5).
 */
export default function UiShowcase() {
  return (
    <main className="mx-auto flex max-w-240 flex-col gap-8 p-4">
      <header className="flex flex-col gap-1">
        <h1 className="m-0 text-title font-bold">Vitrine des composants</h1>
        <p className="m-0 text-body text-text-muted">
          Page de développement : absente de la version de production.
        </p>
      </header>
      <ButtonGallery />
      <TokenPalette />
    </main>
  );
}
