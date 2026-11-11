import { Check, Printer, XCircle } from "lucide-react";
import { Button, type ButtonVariant } from "../../shared/ui";

const VARIANTS: { variant: ButtonVariant; label: string }[] = [
  { variant: "primary", label: "Valider la vente" },
  { variant: "secondary", label: "Imprimer" },
  { variant: "ghost", label: "Plus de détails" },
  { variant: "danger", label: "Annuler la vente" },
];

export function ButtonGallery() {
  return (
    <section aria-labelledby="ui-button" className="flex flex-col gap-4">
      <h2 id="ui-button" className="m-0 text-title-sm font-semibold">
        Button
      </h2>
      {VARIANTS.map(({ variant, label }) => (
        <div key={variant} className="flex flex-wrap items-start gap-2">
          <Button variant={variant}>{label}</Button>
          <Button variant={variant} size="lg">
            {label} (lg)
          </Button>
          <Button variant={variant} disabledReason="Choisissez d'abord un article">
            {label}
          </Button>
          <Button variant={variant} loading>
            {label}
          </Button>
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <Button icon={Check}>Valider</Button>
        <Button variant="secondary" icon={Printer}>
          Imprimer
        </Button>
        <Button variant="danger" icon={XCircle}>
          Passer en perte
        </Button>
      </div>
      <Button size="lg" fullWidth icon={Check}>
        Action principale pleine largeur
      </Button>
    </section>
  );
}
