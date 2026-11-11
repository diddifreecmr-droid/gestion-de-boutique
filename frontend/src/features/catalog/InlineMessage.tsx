import { AlertCircle } from "lucide-react";

/** Erreur d'un groupe ou d'un formulaire, annoncée poliment (design-system.md § 8). */
export function InlineMessage({ text }: { text: string }) {
  return (
    <p role="status" className="m-0 flex items-start gap-1 text-body text-danger-text">
      <AlertCircle aria-hidden="true" className="size-6 shrink-0" />
      <span>{text}</span>
    </p>
  );
}
