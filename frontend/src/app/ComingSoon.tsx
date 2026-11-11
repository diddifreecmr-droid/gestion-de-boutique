import { Construction } from "lucide-react";
import { EmptyState } from "../shared/ui";

/** PROVISOIRE (T12) : écran prévu dont le module n'est pas encore livré (T13 → T22). */
export function ComingSoon({ title }: { title: string }) {
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <EmptyState icon={Construction} message="Cet écran arrive bientôt." />
    </>
  );
}
