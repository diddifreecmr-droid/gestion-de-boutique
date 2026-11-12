import { useRef, type ChangeEvent } from "react";
import type { LucideIcon } from "lucide-react";
import { Button, type ButtonVariant } from "./Button";

export interface FilePickerButtonProps {
  /** Libellé du bouton, aussi nom accessible du sélecteur de fichier. */
  label: string;
  /** Types acceptés (`image/*,application/pdf`) : appareil photo ou galerie sur téléphone. */
  accept: string;
  onFile: (file: File) => void;
  icon?: LucideIcon;
  variant?: ButtonVariant;
  loading?: boolean;
}

/**
 * Choisir ou prendre une photo / un fichier (design-system § 6.1) : bouton du design system,
 * sélecteur natif masqué (le téléphone propose appareil photo, galerie ou fichiers). Le même
 * fichier peut être choisi deux fois de suite (la valeur est vidée après lecture).
 */
export function FilePickerButton(props: FilePickerButtonProps) {
  const { label, accept, onFile, icon, variant = "secondary", loading = false } = props;
  const input = useRef<HTMLInputElement>(null);
  const chosen = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file !== undefined) onFile(file);
  };
  return (
    <>
      <input
        ref={input}
        type="file"
        accept={accept}
        aria-label={label}
        className="sr-only"
        tabIndex={-1}
        onChange={chosen}
      />
      <Button
        variant={variant}
        {...(icon === undefined ? {} : { icon })}
        loading={loading}
        onClick={() => input.current?.click()}
      >
        {label}
      </Button>
    </>
  );
}
