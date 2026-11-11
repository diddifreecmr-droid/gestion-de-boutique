import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <main className="mx-auto flex max-w-150 flex-col gap-4 p-4">
      <h1 className="m-0 text-title font-bold">Page introuvable</h1>
      <p className="m-0 text-body text-text-muted">Cette adresse ne correspond à aucun écran.</p>
      <Link className="text-label font-semibold text-primary underline" to="/">
        Retour à l'accueil
      </Link>
    </main>
  );
}
